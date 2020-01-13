import hashlib
import uuid

from django.utils import timezone
from django.utils.dateparse import parse_datetime
import json
import os

from multiprocessing import Lock
import time

lock = Lock()

def create_lookup(object_model, field_values, lookup_field, existing_lookup=None):
    '''
    An abstracted class for creating a lookup for a given field in a model.
    Note the lookup will only work for fields that are unique.
    If the field does not exist in the database it is created.
    :param object_model: The data model for reference.
    :param field_values: The list if values for the field described in lookup field
    :param lookup_field: The field in the model to create the lookup.
    :param existing_lookup: If an existing lookup exists the is optionally passed to be augmented.
    :return: A dictionary lookup where keys values of the given field and the values are objects.
    '''

    # define the lookup object and assign if existing lookup is given
    lookup = {}
    if existing_lookup:
        lookup = existing_lookup

    # for each of the field values check if it already exist in the lookup.
    # If it doesn't add it by getting or creating in the database.
    for value in field_values:
        if value not in lookup.keys():
            this_item, created = object_model.objects.get_or_create(**{lookup_field: value})
            if created:
                this_item.save()
            lookup[value] = this_item

    return lookup


# ingest companies
def ingest_companies(filename):
    '''
    This simply ingests the latest companies file and returns a lookup dictionary based on the index field.
    It does this by cross referencing the new data with the existing records in the database.
    The model assumes that company name is unique given the limited information in the sample file.
    :param filename: the filename of the companies json file.
    :return: a lookup by the relevant company index
    '''

    from .models import Company

    # Load existing companies and create a lookup for them by name
    company_name_lookup = {}
    existing_companies = Company.objects.all()
    for company in existing_companies:
        company_name_lookup[company.name] = company

    # Read the latest company file and check assumption that the index and names are unique
    with open(filename, 'r') as company_infile:
        new_companies = json.load(company_infile)
        new_company_indexes = [comp['index'] for comp in new_companies]
        assert len(new_companies) == len(list(set(new_company_indexes)))
        new_company_names = [comp['company'] for comp in new_companies]
        assert len(new_companies) == len(list(set(new_company_names)))

    # get or create companies depending whether they already exist in the database.
    # Create a lookup which references the corresponding object object
    company_index_lookup = {}
    for company in new_companies:
        if company['company'] in company_name_lookup.keys():
            this_company = company_name_lookup[company['company']]
        else:
            this_company = Company(name=company['company'])
            this_company.save()
        company_index_lookup[company['index']] = this_company

    return company_index_lookup


def ingest_people(filename, company_lookup):
    '''
    This method loads the people objects into the database.
    It starts by loading all the dependent models like foods, eye_colors, tags and genders and creating quick reference
    lookups for each of them by their names.
    :param filename:
    :param company_lookup:
    :return:
    '''

    from .models import People, Gender, Food, EyeColor, Tag

    # ingest people
    with open(filename, 'r') as people_infile:
        people = json.load(people_infile)

        # Get the unique sets of values for each of the sub models
        # Also create a lookup for the person index with their uuid.
        eyecolors = {}
        genders = {}
        tags = {}
        foods = {}
        people_index_uuid = {}
        for person in people:
            people_index_uuid[person.pop('index')] = uuid.UUID(person['guid'])
            genders[person['gender']] = ''
            eyecolors[person['eyeColor']] = ''
            for tag in person['tags']:
                tags[tag] = ''
            for food in person['favouriteFood']:
                foods[food] = ''

        # create lookups for each of the submodels based on their unique set of values.
        foods_lookup = create_lookup(Food, foods.keys(), 'name')
        tags_lookup = create_lookup(Tag, tags.keys(), 'name')
        gender_lookup = create_lookup(Gender, genders.keys(), 'gender')
        eye_color_lookup = create_lookup(EyeColor, eyecolors.keys(), 'color')

        # Iterate through all people creating objects for them without their friends.
        # Their friends are stored seperately and linked later given the many to 1 self referencing
        person_friends_combos = []
        for person in people:

            # Isolate many to 1 fields of the model as these will need to be added once an object exists
            current_persons_foods = [foods_lookup[this_food].id for this_food in person.pop('favouriteFood')]
            current_persons_tags = [tags_lookup[this_tag].id for this_tag in person.pop('tags')]
            current_persons_friends = [people_index_uuid[friend['index']] for friend in person.pop('friends')]

            # parse the registration datetime
            person['registered'] = parse_datetime(person['registered'].replace(' ', ''))

            # Cast the guid
            person['guid'] = uuid.UUID(person.pop('guid'))

            # Link foreign keys with their corresponding objects through the lookups created earlier
            # TODO speak to the colonies database admin about the consistency of indexing accross the two files.
            person['company'] = company_lookup[person.pop('company_id') - 1]
            person['gender'] = gender_lookup[person['gender']]
            person['eye_color'] = eye_color_lookup[person.pop('eyeColor')]

            # Create a basic (unsaved) instance without the many to 1 relations.
            current_person = People(**person)

            # Check if the person exist already
            person_query = People.active.filter(guid=current_person.guid)

            # if the person already exists check for any changes.
            # Note that many to 1 fields require explicit comparison as the the instance in question is not saved/
            if len(person_query):
                existing_person = person_query[0]

                # These checks on many to 1 fields need to be performed here to correctly update or create.
                # i.e. Foreign key constraints restrict the addition of other objects before the principle object has been committed.
                # AND Committing each person in a scoped session would create too much of an time/performance overhead for this startup script.
                existing_foods = [food.id for food in existing_person.favourite_food.all()]
                existing_tags = [tag.id for tag in existing_person.tags.all()]
                existing_friends = [friend.guid for friend in existing_person.friends.all()]

                # If the new set has a different person or models shut out the old record and commit the new one
                if not (current_person == existing_person
                        and set(existing_foods) == set(current_persons_foods)
                        and set(existing_friends) == set(current_persons_friends)
                        and set(existing_tags) == set(current_persons_tags)):
                    existing_person.updated_at = timezone.now()
                    existing_person.active = False
                    existing_person.save()

                    current_person.save()
                    current_person.tags.set(current_persons_tags)
                    current_person.favourite_food.set(current_persons_foods)
                    current_person.save()
                    # add the person friend combos to be added later.
                    person_friends_combos.append((current_person, current_persons_friends))

            # The record doesn't exist at all ... save the person
            else:
                current_person.save()
                current_person.tags.set(current_persons_tags)
                current_person.favourite_food.set(current_persons_foods)
                current_person.save()
                # add the person friend combos to be added later.
                person_friends_combos.append((current_person, current_persons_friends))

        # add the friends to each person now that a database record exist for all of them
        for (person, friends) in person_friends_combos:
            person.friends.set([friend.id for friend in People.active.filter(guid__in=friends)])
            person.save()


def get_hash(filename):
    '''
    Gets the md5 hash of a file and returns it.
    :param filename: The file to be hashed
    :return: the hexidecimal hash string of the file
    '''
    hasher = hashlib.md5()
    with open(filename, 'rb') as afile:
        buf = afile.read()
        hasher.update(buf)
    return hasher.hexdigest()


def ingest_data():
    '''
    Manage the ingestions of data files.
    Given a companies and a people file it checks to see if the file pair has been ingested together before.
    If it has it skips ingesting the files for a faster initialisation.
    # TODO get the static/resources directory into a configuration or settings file or system variable.
    '''
    from .models import IngestedFiles

    # Define the filepaths
    resource_directory = './static/resources'
    company_file = os.path.join(resource_directory, 'companies.json')
    people_file = os.path.join(resource_directory, 'people.json')

    # Take hashes of the two files.
    companyfile_hash = get_hash(company_file)
    peoplefile_hash = get_hash(people_file)

    # If the file combination has not been ingested before process them now.
    if not len(IngestedFiles.objects.filter(companyfile_hash=companyfile_hash, peoplefile_hash=peoplefile_hash)):

        # Ingest the files... order is important here.
        company_lookup = ingest_companies(company_file)
        ingest_people(people_file, company_lookup)

        # save the uploaded set for future reference
        upload_set = IngestedFiles(companyfile_hash=companyfile_hash, peoplefile_hash=peoplefile_hash)
        upload_set.save()

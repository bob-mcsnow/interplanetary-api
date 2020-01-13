import uuid

from django.http import JsonResponse, Http404, HttpResponse

# Create your views here.
from .models import Company, People, EyeColor


def company(request, company_name):
    '''
    An endpoint for the company.
    :param request: Incoming request object
    :param company_name: The case-sensitve company name
    :return: JsonResponse object containing with a payload of the following format...
            {"company" : '', "employees": [{"name":''}...]}
    '''
    # Check if the company exist or raise a 404
    try:
        company = Company.objects.get(name=company_name)
    except Company.DoesNotExist:
        raise Http404('Company, {}, does not exist'.format(company_name))

    # get employees and structure response. I have included the company name in the response object as no specification was given here.
    employees = People.active.filter(company=company).all().values('name')
    response = {'company': company_name, 'employees': list(employees)}

    return JsonResponse(response, safe=False)


def validate_people(person_uuids):
    '''
    Validate a list of people by their GUIDs.
    Checks if the supplied guid is a valid guid and that it exists in the database.
    Raises a 404 with appropriate response if either fails.
    :param person_uuids: a list of uuids as strings
    '''
    for person in person_uuids:
        error = None
        try:
            this_uuid = uuid.UUID(person)
            try:
                People.active.get(guid=this_uuid)
            except People.DoesNotExist:
                error = 'No record for person: {}'.format(this_uuid)
        except ValueError:
            error = '{} : is not a valid guid. Check that it is not malformed'.format(person)

        if error:
            raise Http404(error)


def commonfriends(request, people_uuids):
    '''
    For two or more people returns their information along with a list of their common friends who have alive and
    have brown eyes. A weird endpoint... Perhaps for the geneticists in Checktoporov.
    :param request: Incoming request object
    :param people_uuids: A colon seperated list of guids for the people data set.
    :return: JsonResponse object containing with a payload of the following format...
            {
             "individuals_details" : [{"name":"", "age":"", "address":"","phone":""}..],
             "common_browneyed_alive_friends" : [{"name":""}...]
             }
    '''

    # Parse the uuids into a list and validate them.
    input_uuids = people_uuids.split(':')
    validate_people(input_uuids)

    # Retrieve the queryset for the people.
    people = People.active.filter(guid__in=input_uuids)

    # Make a list of friend sets for each of the people.
    friend_sets = []
    for person in people:
        friend_sets.append(set([friend.guid for friend in
                                person.friends.filter(eye_color=EyeColor.objects.get(color='brown'), has_died=False)]))

    # Consolidate the friend sets by retaining on friends common across all sets.
    reference_set = friend_sets[0]
    for f_set in friend_sets[1:]:
        reference_set = reference_set.intersection(f_set)

    # Retrieve the actual names of the friends
    common_friends = People.active.filter(guid__in=list(reference_set)).values('name')

    # Structure the response
    response = {"individuals_details": list(people.values('name', 'age', 'address', 'phone')),
                "common_browneyed_alive_friends": list(common_friends)
                }

    return JsonResponse(response, safe=False)


def favourite_foods(request, person_uuid):
    '''
    For a given person this endpoint return a list of their favorite foods and their age.
    :param request: Incoming request object
    :param person_uuid: The uuid of the person
    :return: JsonResponse object containing with a payload of the following format...
            {"name": "", "age": , "vegetables": [...], "fruits": [...]}
    '''
    # Validate the given uuid and retrieve the person
    validate_people([person_uuid])
    person = People.active.get(guid=person_uuid)

    # Categorise the persons foods into a dictionary
    categorised_foods = {}
    for food in person.favourite_food.all():
        label = '{}s'.format(food.FoodTypes(food.food_type).label.lower())
        if label not in categorised_foods:
            categorised_foods[label] = []
        categorised_foods[label].append(food.name)

    # Create a response and populate it with all categories of food.
    response = {'name': person.name, 'age': person.age}
    for category, food_list in categorised_foods.items():
        response[category] = food_list

    return JsonResponse(response)

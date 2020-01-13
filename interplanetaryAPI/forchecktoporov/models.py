import uuid

from django.db import models

# Create your models here.
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    '''
    The company model. Given limited info assumes uniqueness in name
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(verbose_name='company', max_length=100, unique=True)

    class Meta:
        ordering = ['name']


class CurrencyField(models.Field):
    '''
    A custom currency field to store currencies as floats rather than strings.
    '''

    def db_type(self, connection):
        return 'float'

    def get_db_prep_value(self, value, *args, **kwargs):
        return float(value[1:].replace(',', ''))

    def to_python(self, value):
        return '${:,.2f}'.format(value)

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)


class OnlyActiveManager(models.Manager):
    '''
    A manager to isolate active records.
    An active flag has been given to people to facilitate historical database records.
    '''
    def get_queryset(self):
        return super(OnlyActiveManager, self).get_queryset().filter(is_active=True)


class People(models.Model):
    '''
    The people model.
    guid is used to identify individuals while an additional uuid - id field is used to keep track of historical records.
    Custom equal function has been written to compare active data fields
    '''
    _id = models.CharField(max_length=24)  # Unclear what this is used for
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guid = models.UUIDField(default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=70)
    eye_color = models.ForeignKey('EyeColor', on_delete=models.SET_NULL, null=True, verbose_name='eyeColor')
    gender = models.ForeignKey('Gender', on_delete=models.SET_NULL, null=True)
    company = models.ForeignKey('Company', on_delete=models.SET_NULL, null=True)
    friends = models.ManyToManyField('self', through='PeopleToFriend', symmetrical=False)
    has_died = models.BooleanField(verbose_name='is_deceased', null=True)
    balance = CurrencyField(default=0.0)
    picture = models.URLField()
    age = models.IntegerField()
    email = models.EmailField()
    phone = models.CharField(max_length=17)
    address = models.CharField(max_length=300)
    about = models.TextField()
    registered = models.DateTimeField()
    tags = models.ManyToManyField('Tag')
    greeting = models.CharField(max_length=250)
    favourite_food = models.ManyToManyField('Food', through='PeopleToFood')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    object = models.Manager()
    active = OnlyActiveManager()

    def __eq__(self, other):
        field_not_compared = ['created_at', 'updated_at', 'id', '_state']
        mydict = {k: v for k, v in self.__dict__.items() if k not in field_not_compared}
        otherdict = {k: v for k, v in other.__dict__.items() if k not in field_not_compared}
        return mydict == otherdict

    class Meta:
        ordering = ['name']
        verbose_name = 'Person'


class EyeColor(models.Model):
    '''The model for eye color'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    color = models.CharField(max_length=10, unique=True)


class Gender(models.Model):
    '''The model for gender'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gender = models.CharField(max_length=15, unique=True)


class Tag(models.Model):
    '''The model for tags'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30, unique=True)

class Food(models.Model):
    '''
    The food model.
    Uses an "enum" for food types
         an internal lookup for food type classification. This should be built out in the future.
         a custom save method which assigns the food type if it in the lookup.
    '''
    class FoodTypes(models.TextChoices):
        FRUIT = 'fr', _('Fruit')
        VEGETABLE = 've', _('Vegetable')
        UNCLASSIFIED = 'un', _('Unclassified')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=20)
    food_type = models.CharField(max_length=2, choices=FoodTypes.choices, default=FoodTypes.UNCLASSIFIED)

    __type_lookup__ = {'orange': FoodTypes.FRUIT,
                       'beetroot': FoodTypes.VEGETABLE,
                       'strawberry': FoodTypes.FRUIT,
                       'cucumber': FoodTypes.VEGETABLE,
                       'celery': FoodTypes.VEGETABLE,
                       'banana': FoodTypes.FRUIT,
                       'carrot': FoodTypes.VEGETABLE,
                       'apple': FoodTypes.FRUIT,
                       }

    def save(self, *args, **kwargs):
        if self.name in self.__type_lookup__.keys():
            self.food_type = self.__type_lookup__[self.name]
        super(Food, self).save(*args, **kwargs)


class PeopleToFood(models.Model):
    '''
    Many to 1 through table for people's favourite foods.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey('People', on_delete=models.CASCADE)
    food = models.ForeignKey('Food', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('person', 'food')


class PeopleToFriend(models.Model):
    '''
    Many to many through table for people's friends
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey('People', on_delete=models.CASCADE, related_name='person')
    friend = models.ForeignKey('People', on_delete=models.CASCADE, related_name='friend')

    class Meta:
        unique_together = ('person', 'friend')

class IngestedFiles(models.Model):
    '''
    A record of ingested files. Helps speed up load time when files have already been loaded.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    companyfile_hash = models.CharField(max_length=256)
    peoplefile_hash = models.CharField(max_length=256)
    ingested_on = models.DateTimeField(default=now)

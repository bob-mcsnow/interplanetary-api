
This is an api for the people of paranuara to give information about people and companies back to the people in checktoporov.

It is written in DJANGO and deployment is managed through docker and docker-compose. 
At present it is configured to use a postgresql database. 

## Inputs
Provided by the people of paranuara in two files:
* people.json
* companies.json

These files should be places in the directory...

    static/resources/ 

## Deploying the application.

#### With docker
The configuration of the deployment is managed through the `docker-compose.yml` file along with the `env_file.env` files.
You will require docker and docker compose to run the application. As this is system dependant you should refer to the 
installation guides for [docker](https://docs.docker.com/install/) and [docker compose](https://docs.docker.com/compose/install/).

Note that my point of contact said it should be fine to use docker even though it part of your standard environment. 
If this is a problem please let me know and I will be more than happy to rewrite the deployment instructions for a 
virtual-env style deployment. 

Once docker is installed you can simply run...

    docker-compose build
    
and 

    docker-compose up
    
To run the application. With the current configuration the endpoints should be available at `localhost:2222/endpoints` .

#### ENDPOINTS

The three end points in the specification are...

###### Company employees:

`localhost:2222/forchecktoporov/company/<company_name>/`

###### Common alive brown eyed friends: 
*Note that this endpoint needs two or more guids seperated by colons (`:`)*

`localhost:2222/forchecktoporov/common-friends/<colon_seperate_people_uuids>/`

###### Favorite foods:

`localhost:2222/forchecktoporov/common-friends/<persons_uuid>/`
    
### Persisted state

Data is persisted in the database which is currently configured (under a postgresql database instance) 
to be stored here...

    db/postgres/pgdata

The database uses `active` records and created_at/updated_at to maintain a historical record of the data. 
I.e. when information is updated on people or new records provided this is added to the existing historical data.  

To change the database you will need to create a new database container and modify the database environment 
variables (and add new ones) in `env_file.env`. 

### Caveats and troubleshooting
Note that the permissions on the shared database volume are overwritten by docker on every deployment.
So if you need to run `docker-compose build` after making some changes you will need to run it as root or admin to 
maintain the persisted database. This is also true if you need to delete the database. 

### TODOs 

Unfortunately I have spend a little longer than I am able to on this challenge already so below are a few areas where 
I would continue working...

 
* LOGGING: While there is standard outputs in a number of places a formal logging structure would be nice
* TESTS: These are pretty essential for ongoing maintenance and development of the application.
* STARTUP SCRIPT: At the moment the data ingestion logic is coupled to the initialisation of the app. This works fine for 
development purposes, but it causes database consistency errors when initiallising the 3 gunicorn workers for deployment.
While this could be solved with scoped session or a mutex it would be better to run this as a seperate process in the 
shell before running gunicorn.  
* MIGRATIONS: At the moment migrations are forced to run everytime the application is spun up. The developer needs to edit 
the command in the `docker-compose.yml` to manage this. In my opinion this is bad practice and migrations should be 
manually performed in isolation.  
* ENVIRONMENT FILE: This is obviously bad practice to store this config in plain sight. I would look to `git-secret` or`git-crypt`. 
 


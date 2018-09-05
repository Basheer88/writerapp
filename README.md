# Writer App 
-----------------------
This is simple app used by all people who want a palce to write whatever they want without any restriction. This app programmed using python and flask framework.

## Requirments
python version 3 ( Can be download from [here](https://www.python.org/downloads/))

virtual Environment.

## DataBase
DataBase ( named **writerDB** ) includes two tables:
* **Author** table includes information about the writer 
 ```
 id (type: integer) Primary Key
 name (type: text) not null
 email (type: text) not null
 picture (type: text)
 ```

* **Post** table includes all posts
 ```
 id (type: integer) Primary Key
 title (type: text) not null
 description (type: text) not null
 author_id (type: integer) Foregin key =>(Author.id)
 ```

## Installation
download or Clone the GitHub repository

https://github.com/Basheer88/writerapp.git

install all the requirment package ( pip install -r requirements.txt )

# Files of the repository
database_setup : to generate an empty database run ( python database_setup)

initial_info : this will add one entry to the empty database. can be used to help you understand how to add entry to the database. run ( python initial_info.py)

WriterApp file : this file to make the app working. first run (run python SpaceApp.py) then access the app using (localhost:8000)


# License
Free license. Feel free to do whatever you want with it.
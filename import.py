# Importing 5000 books to DB from CSV file

import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine("postgres://nwxnjdwochgocs:83ebb2ae24471f7872b0b2213e81e590187bffe71a7fccf2b7b8e62ae638207a@ec2-34-232-147-86.compute-1.amazonaws.com:5432/d6f019qvcptvf7")
db = scoped_session(sessionmaker(bind=engine))


f = open("books.csv")
read = csv.reader(f)


for isbn, title, author, year in read:
    db.execute("INSERT INTO bookdetails (isbn, title, author, year) VAlUES (:isbn, :title, :author, :year)", 
    {
        "isbn": isbn,
         "title":title, 
         "author":author, 
         "year":year
                })
    db.commit()


print("added")

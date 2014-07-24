#!/bin/bash

/etc/init.d/postgresql start

psql --command "CREATE USER sams WITH SUPERUSER PASSWORD 'sams';"

createdb -O sams sams

psql -l

for i in /sql/tables/*.sql
do
    psql --file=$i --dbname=sams
done

for i in /sql/static_data/*.sql
do
    psql --file=$i --dbname=sams
done

/etc/init.d/postgresql stop

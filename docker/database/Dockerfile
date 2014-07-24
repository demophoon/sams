# SAMS Database
# Development Docker File
#
# Use this for development only, there are no guarantees
# that this will be stable or secure enough for a production
# environment.

FROM postgres:9.3.4
MAINTAINER Britt Gresham <brittcgresham@gmail.com>

ADD ./setup.sh /setup.sh
RUN chmod +x /setup.sh
RUN /setup.sh

EXPOSE 5432
CMD ["/usr/lib/postgresql/9.3/bin/postgres", "-D", "/var/lib/postgresql/9.3/main", "-c", "config_file=/etc/postgresql/9.3/main/postgresql.conf"]

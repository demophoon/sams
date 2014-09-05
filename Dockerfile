# SAMS
# Development Docker File
#
# Use this for development only, there are no guarantees
# that this will be stable or secure enough for a production
# environment.

FROM ubuntu:14.04
MAINTAINER Britt Gresham <brittcgresham@gmail.com>

RUN apt-get update --fix-missing
RUN apt-get install git python python-dev python-pip -y
RUN pip install virtualenv

RUN virtualenv /opt/sams/
RUN /opt/sams/bin/pip install gevent

RUN mkdir /opt/sams/src/
ADD . /opt/sams/src/
WORKDIR /opt/sams/src/

# We will run with `install` since we will just rebuild the
# container after we update the codebase anyways
RUN /opt/sams/bin/python setup.py install

# Initialize Database Model
RUN /opt/sams/bin/initialize_sams_db production.ini

EXPOSE 6543
ENTRYPOINT ["/opt/sams/bin/pserve"]
CMD ["production.ini"]

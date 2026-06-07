# Apache Spark image + numpy, which pyspark.ml (the regression job) requires but
# the base image does not ship. numpy 1.24.x is the last line supporting the
# image's Python 3.8.
FROM apache/spark:3.5.3

USER root
RUN python3 -m pip install --no-cache-dir numpy==1.24.4
USER spark

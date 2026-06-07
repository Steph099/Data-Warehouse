"""Spark ML regression job.

Trains a LinearRegression on one asset's latest-per-day series (tombstones excluded)
to predict the day's `open` from (seconds, close, low, high), and writes test-set
predictions to `regression_results`. Configure via env ASSET_ID / DATA_SOURCE_ID
(default BTCUSD / BITFINEX); see README / docker-compose for the spark-submit command.
"""
import os

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import Normalizer, VectorAssembler
from pyspark.ml.regression import LinearRegression
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def main() -> None:
    keyspace = os.environ.get("CASSANDRA_KEYSPACE", "acme_dwh")
    asset_id = os.environ.get("ASSET_ID", "BTCUSD")
    data_source_id = os.environ.get("DATA_SOURCE_ID", "BITFINEX")

    spark = SparkSession.builder.appName("acme-dwh-regression").getOrCreate()

    data = (
        spark.read.format("org.apache.spark.sql.cassandra")
        .options(table="data", keyspace=keyspace)
        .load()
        .filter((F.col("asset_id") == asset_id) & (F.col("data_source_id") == data_source_id))
    )

    latest_per_day = Window.partitionBy("business_date").orderBy(F.col("system_time").desc())
    latest = (
        data.withColumn("_rn", F.row_number().over(latest_per_day))
        .filter(F.col("_rn") == 1)
        .filter(~F.coalesce(F.col("deleted"), F.lit(False)))
    )

    df = (
        latest.select(
            F.col("values_double")["open"].alias("open"),
            F.col("values_double")["close"].alias("close"),
            F.col("values_double")["low"].alias("low"),
            F.col("values_double")["high"].alias("high"),
            F.unix_timestamp(F.col("business_date").cast("timestamp")).alias("seconds"),
            F.col("business_date"),
        )
        .na.drop()
    )

    if df.count() < 10:
        print(f"[regression] not enough data for {asset_id}/{data_source_id} (need >=10 rows).")
        spark.stop()
        return

    features = VectorAssembler(
        inputCols=["seconds", "close", "low", "high"], outputCol="features"
    ).transform(df)
    normalized = Normalizer(inputCol="features", outputCol="normFeatures", p=2.0).transform(features)

    train, test = normalized.randomSplit([0.7, 0.3], seed=42)
    lr = LinearRegression(
        labelCol="open", featuresCol="normFeatures", maxIter=10, regParam=1.0, elasticNetParam=1.0
    )
    model = lr.fit(train)
    predictions = model.transform(test)

    rmse = RegressionEvaluator(
        labelCol="open", predictionCol="prediction", metricName="rmse"
    ).evaluate(predictions)

    results = predictions.select(
        F.lit(asset_id).alias("asset_id"),
        F.lit(data_source_id).alias("data_source_id"),
        F.col("seconds").cast("long").alias("seconds"),
        F.col("business_date"),
        F.col("open"),
        F.col("prediction"),
    )
    (
        results.write.format("org.apache.spark.sql.cassandra")
        .options(table="regression_results", keyspace=keyspace)
        .mode("append")
        .save()
    )

    print(f"[regression] {asset_id}/{data_source_id}: wrote {results.count()} predictions; RMSE={rmse:.4f}")
    results.orderBy("seconds").show(20, truncate=False)
    spark.stop()


if __name__ == "__main__":
    main()

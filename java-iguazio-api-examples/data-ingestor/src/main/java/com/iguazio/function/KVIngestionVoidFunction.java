package com.iguazio.function;

import org.apache.spark.api.java.JavaRDD;
import org.apache.spark.api.java.function.VoidFunction;
import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.SparkSession;

import com.iguazio.bo.Car;

public class KVIngestionVoidFunction implements VoidFunction<JavaRDD<Car>> {

	@Override
	public void call(JavaRDD<Car> rdd) throws Exception {
		rdd.cache();
		SparkSession session = new SparkSession(rdd.context());
		Dataset<Row> df = session.createDataFrame(rdd, Car.class);

		df.write().format("io.iguaz.v3io.spark.sql.kv").mode("append").option("key", "driverId").save("/cars-kv");

		System.out.println("count is " + df.count());

	}

}

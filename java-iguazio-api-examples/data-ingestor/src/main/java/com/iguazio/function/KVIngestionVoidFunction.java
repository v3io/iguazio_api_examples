/*
Copyright 2017 Iguazio Systems Ltd.

Licensed under the Apache License, Version 2.0 (the "License") with
an addition restriction as set forth herein. You may not use this
file except in compliance with the License. You may obtain a copy of
the License at http://www.apache.org/licenses/LICENSE-2.0.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied. See the License for the specific language governing
permissions and limitations under the License.

In addition, you may not use the software for any purposes that are
illegal under applicable law, and the grant of the foregoing license
under the Apache 2.0 license is conditioned upon your compliance with
such restriction.
*/
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

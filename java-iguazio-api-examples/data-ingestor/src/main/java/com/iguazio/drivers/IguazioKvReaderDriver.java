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
package com.iguazio.drivers;

import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.SQLContext;
import org.apache.spark.sql.SparkSession;

public class IguazioKvReaderDriver {

	private SparkSession session;

	public IguazioKvReaderDriver() {

		init();
	}

	public void init() {

		this.session = SparkSession.builder().master("local[*]").appName("IguazioApiTest").getOrCreate();

	}

	public static void main(String[] args) {
		IguazioKvReaderDriver driver = new IguazioKvReaderDriver();
		driver.run();

	}

	public void run() {

		SQLContext sqlCtx = new SQLContext(session);

		Dataset<Row> df = sqlCtx.read().format("io.iguaz.v3io.spark.sql.kv").load("/cars-kv");
		df.show(10);

	}

}

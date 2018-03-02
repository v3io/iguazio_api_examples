package com.iguazio.drivers;

import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.SQLContext;
import org.apache.spark.sql.SparkSession;

public class DataFrameReaderDriver {

	private SparkSession session;

	public DataFrameReaderDriver() {

		init();
	}

	public void init() {

		this.session = SparkSession.builder().master("local[*]").appName("IguazioApiTest").getOrCreate();

	}

	public static void main(String[] args) {
		DataFrameReaderDriver driver = new DataFrameReaderDriver();
		driver.run();

	}

	public void run() {

		SQLContext sqlCtx = new SQLContext(session);

		Dataset<Row> df = sqlCtx.read().format("io.iguaz.v3io.spark.sql.kv").load("/cars-test");
		df.show();

	}

}

package com.iguazio.function;

import org.apache.spark.api.java.JavaRDD;
import org.apache.spark.api.java.function.VoidFunction;

public class IguazioStreamVoidFunction implements VoidFunction<JavaRDD<String>> {

	@Override
	public void call(JavaRDD<String> cars) throws Exception {

		System.out.println("count is " + cars.count());

	}

}

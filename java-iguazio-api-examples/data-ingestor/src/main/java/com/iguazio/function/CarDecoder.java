package com.iguazio.function;

import java.nio.charset.Charset;
import java.util.Properties;

import com.iguazio.bo.Car;

import io.iguaz.v3io.spark.streaming.Decoder;
import scala.Function1;
import scala.Option;

public class CarDecoder implements Decoder<Car> {

	@Override
	public Charset encoding(Option<Properties> arg0) {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	public Option<Properties> encoding$default$1() {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	public Car fromBytes(byte[] arg0, Function1<Option<Properties>, Charset> arg1) {
		return new Car(new String(arg0).split(","));
	}

}

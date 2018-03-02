package com.iguazio.bo;

public class Car {

	private String color;
	private String vendor;
	private int mfgYear;
	private String state;
	private long carId;
	private long speed;

	public Car(String[] arr) {
		this.carId = new Long(arr[0]);
		this.color = arr[1];
		this.vendor = arr[2];
		this.mfgYear = new Integer(arr[3]);
		this.state = arr[4];
		this.speed = new Long(arr[5]);

	}

	public String getColor() {
		return color;
	}

	public void setColor(String color) {
		this.color = color;
	}

	public String getVendor() {
		return vendor;
	}

	public void setVendor(String vendor) {
		this.vendor = vendor;
	}

	public int getMfgYear() {
		return mfgYear;
	}

	public void setMfgYear(int mfgYear) {
		this.mfgYear = mfgYear;
	}

	public String getState() {
		return state;
	}

	public void setState(String state) {
		this.state = state;
	}

	public long getCarId() {
		return carId;
	}

	public void setCarId(long carId) {
		this.carId = carId;
	}

	public long getSpeed() {
		return speed;
	}

	public void setSpeed(long speed) {
		this.speed = speed;
	}

	@Override
	public int hashCode() {
		final int prime = 31;
		int result = 1;
		result = prime * result + (int) (carId ^ (carId >>> 32));
		return result;
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if (obj == null)
			return false;
		if (getClass() != obj.getClass())
			return false;
		Car other = (Car) obj;
		if (carId != other.carId)
			return false;
		return true;
	}

	@Override
	public String toString() {
		return carId + ", " + color + ", " + vendor + ", " + mfgYear + ", " + state + ", " + speed;
	}

}

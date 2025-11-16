package main

func AbsDiffInt(x, y int) int {
	if x < y {
		return y - x
	}
	return x - y
}

func EqualityCoefficientFloat64(a, b any) float64 {
	if a == b {
		return 1
	}
	return 0
}

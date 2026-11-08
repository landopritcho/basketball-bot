// Package date handles all internal date and datetime functions
package date

import "time"

var centralTimezone = func() *time.Location {
	location, err := time.LoadLocation("America/Chicago")
	if err != nil {
		panic(err)
	}
	return location
}()

func GetCurrentCondensedDate() string {
	now := time.Now()
	return now.Format("20060102")
}

func GetCurrentCalendarDate() string {
	now := time.Now()
	return now.Format("2006-01-02")
}

func GetTomorrowsCondensedDate() string {
	now := time.Now()
	return now.AddDate(0, 0, 1).Format("20060102")
}

func GetTomorrowCalendarDate() string {
	now := time.Now()
	return now.AddDate(0, 0, 1).Format("2006-01-02")
}

func ConvertUTCDatetimeToCentralDatetime(datetime string) (string, error) {
	parsedDatetime, err := time.Parse("2006-01-02T15:04Z07:00", datetime)
	if err != nil {
		return "", err
	}
	return parsedDatetime.In(centralTimezone).Format("Jan 2, 2006 3:04 PM MST"), nil
}

func ConvertCentralDatetimeToUnix(datetime string) (int64, error) {
	parsedDatetime, err := time.ParseInLocation("Jan 2, 2006 3:04 PM MST", datetime, centralTimezone)
	if err != nil {
		return 0, err
	}
	return parsedDatetime.Unix(), nil
}

func ConvertUnixToCentralDatetime(datetime int64) (string, error) {
	parsedDatetime := time.Unix(datetime, 0)
	return parsedDatetime.In(centralTimezone).Format("Jan 2, 2006 3:04 PM MST"), nil
}

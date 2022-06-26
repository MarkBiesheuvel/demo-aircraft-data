WITH longitude_history AS (
    SELECT BIN(time, 1m) AS binned_timestamp, ROUND(AVG(measure_value::double), 3) AS Longitude
    FROM "aircraft-database"."aircraft-table"
    WHERE measure_name = 'Longitude'
  		AND time > ago(1h)
    	AND IcaoAddress = '440170'
	GROUP BY BIN(time, 1m)
  ),
  latitude_history AS (
    SELECT BIN(time, 1m) AS binned_timestamp, ROUND(AVG(measure_value::double), 3) AS Latitude
    FROM "aircraft-database"."aircraft-table"
    WHERE measure_name = 'Latitude'
  		AND time > ago(1h)
    	AND IcaoAddress = '440170'
	GROUP BY BIN(time, 1m)
  )
SELECT longitude_history.binned_timestamp,
	longitude_history.Longitude,
	latitude_history.Latitude
FROM longitude_history
INNER JOIN latitude_history ON longitude_history.binned_timestamp = latitude_history.binned_timestamp
ORDER BY binned_timestamp

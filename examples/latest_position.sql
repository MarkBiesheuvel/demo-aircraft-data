WITH latest_longitude AS (
    SELECT IcaoAddress, max(time) as max_time
    FROM "aircraft-database"."aircraft-table"
    WHERE measure_name = 'Longitude' AND time > ago(1h)
    GROUP BY IcaoAddress
  ),
  latest_latitude AS (
    SELECT IcaoAddress, max(time) as max_time
    FROM "aircraft-database"."aircraft-table"
    WHERE measure_name = 'Latitude' AND time > ago(1h)
    GROUP BY IcaoAddress
  ),
  latest_heading AS (
    SELECT IcaoAddress, max(time) as max_time
    FROM "aircraft-database"."aircraft-table"
    WHERE measure_name = 'Heading' AND time > ago(1h)
    GROUP BY IcaoAddress
  ),
  longitude_view AS (
    SELECT a.IcaoAddress, a.measure_value::double
    FROM "aircraft-database"."aircraft-table" AS a
    INNER JOIN latest_longitude AS l ON l.max_time = a.time
    WHERE a.measure_name = 'Longitude' AND time > ago(1h)
  ),
  latitude_view AS (
    SELECT a.IcaoAddress, a.measure_value::double
    FROM "aircraft-database"."aircraft-table" AS a
    INNER JOIN latest_latitude AS l ON l.max_time = a.time
    WHERE a.measure_name = 'Latitude' AND time > ago(1h)
  ),
  heading_view AS (
    SELECT a.IcaoAddress, a.measure_value::bigint
    FROM "aircraft-database"."aircraft-table" AS a
    INNER JOIN latest_heading AS l ON l.max_time = a.time
    WHERE a.measure_name = 'Heading' AND time > ago(1h)
  )
SELECT longitude_view.IcaoAddress,
  longitude_view.measure_value::double AS Longitude,
  latitude_view.measure_value::double AS Latitude,
  heading_view.measure_value::bigint AS Heading
FROM longitude_view
INNER JOIN latitude_view ON longitude_view.IcaoAddress = latitude_view.IcaoAddress
INNER JOIN heading_view ON longitude_view.IcaoAddress = heading_view.IcaoAddress

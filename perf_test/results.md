### Results using this query with 20 requests:

`SELECT 
  MAX(successfully_finished_at) - MIN(created_at) AS time_difference
FROM feed_uploads
WHERE successfully_finished_at > TIMESTAMPTZ '{time when we have send the first request};`

#### Results from consumer: 00:00:10.622888 (seconds)

#### Results from consumer_v2: 00:00:49.050087 (seconds)
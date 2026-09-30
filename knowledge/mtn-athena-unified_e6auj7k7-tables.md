# MTN SA — Athena `unified_e6auj7k7` database: table inventory

Reusable reference of every table in the `unified_e6auj7k7` Athena database (MTN SA project, accessed via `athena-mcp-server` with `project="mtn"`, profile `clarissa-insights-product`, region
`eu-central-1`). Detailed query definitions and registered-query implementations live in `aws-access-cli/scripts/athena_runner/` (see `queries/playback_outcome.py` and `shaka_errors/`) — this file
only distills the "what tables exist / what are they for" fact so future investigations don't have to rediscover it via `SHOW TABLES`.

## How this was discovered

```sql
SHOW TABLES IN unified_e6auj7k7
```
run via `athena-mcp-server-run_athena_sql` (project `mtn`), 2026-09-07.

## Tables by category

### Core / unified
- `unified_sessions` — session-level unified fact table. Used by the registered `playback-outcome` query (`athena_runner.queries.playback_outcome`); a known VSF-misclassification gap in that query is
  documented in `knowledge/mtn-adoption-playback-outcome-classification-gap.md`; columns include `parent_session_id`, `user_id`, `device_id`, `content`, `event_type`, `endreason`, `event_start`,
  `event_end`, `timestamp_formatted` (date partition key).
- `unified_applications`
- `unified_navigation_steps`

### Debug / errors
- `e6auj7k7_ccl_debug_events` — current-month Shaka player debug/error events. Used by `athena_runner.shaka_errors.query`. Key columns: `eventid` (filter `= 'PLAYER_ERROR'`), `eventdata` (JSON; error
  code at `json_extract_scalar(eventdata, '$.errorcode')`), `clientid` (household id derivable via `split_part(clientid, ':', 2)`), `datetime` (ISO8601 UTC, e.g. `'2026-09-05T00:00:00.000Z'`).
- `e6auj7k7_ccl_debug_events_aug26` — same shape, historical month (August 2026). Historical months live in separately-named tables like this; pass the table name explicitly when querying older data
  (see `ShakaErrorCodeQuery.__init__`'s `table` param).

### Fact tables
- `fact_applications`
- `fact_downloads`
- `fact_navigation_interactions`
- `fact_navigation_journeys`
- `fact_navigation_steps`
- `fact_navigation_to_features`
- `fact_sessions`
- `fact_sessions_export_20260124` (point-in-time export snapshot)
- `fact_ui_sessions`

### Report / aggregate tables (`rep_*`)
- `rep_channelhour_agg` (+ `rep_channelhour_agg_export_20260124`)
- `rep_daily_content_agg_details`
- `rep_daily_device_1d_base_agg`
- `rep_daily_device_7d_base_agg`
- `rep_daily_device_30d_base_agg`
- `rep_daily_device_agg` (+ `rep_daily_device_agg_export_20260124`)
- `rep_daily_feature_agg`
- `rep_daily_session_agg` (+ `rep_daily_session_agg_export_20260124`)
- `rep_device_attributes_daily_agg`
- `rep_devices_agg` (+ `rep_devices_agg_export_20260124`)
- `rep_hourly_journey_aggregation`
- `rep_hourly_screens_aggregation`
- `rep_hourly_swimlane_aggregation`
- `rep_household_device_base_agg`
- `rep_mau_agg` (monthly active users)
- `rep_mtd_agg` (month-to-date)
- `rep_op_concurrency_insights_agg`
- `rep_op_daily_active_dev_agg`
- `rep_op_insights_agg`
- `rep_top_channel_device_agg` (+ `rep_top_channel_device_agg_export_20260426`)

### Dimension / lookup tables
- `channel_ranks`
- `country_data`
- `device_attributes`
- `device_data` (+ `device_data_view_trino` — Trino-compatible view variant, `temp_device_data_table` — working copy)
- `ip_data` (+ `temp_ip_data_table` — working copy)

### App-insights temp tables
- `app_insights_temp_applications`
- `app_insights_temp_downloads`
- `app_insights_temp_sessions`

### Other temp tables
- `temp_linked_navigation_sessions`
- `temp_navigation_sessions`
- `temp_navigation_steps`

### Views
- `vw_top10_unique_content`

## Gotchas

- `_export_<date>` and `_augNN`-suffixed tables are point-in-time snapshots/historical-month copies, not live tables — don't assume they auto-update.
- `errorcode` in `e6auj7k7_ccl_debug_events` is nested in the `eventdata` JSON blob, not a top-level column — always go through `json_extract_scalar(eventdata, '$.errorcode')`.
- Household ID isn't a direct column in the debug-events table; it's derived from `clientid` via `split_part(clientid, ':', 2)` (see `athena_runner.shaka_errors.query.for_hhid`).

Source: Copilot CLI session 2026-09-07 (project `mtn`), cross-referenced against `aws-access-cli/scripts/athena_runner/queries/playback_outcome.py` and
`aws-access-cli/scripts/athena_runner/shaka_errors/*.py`.

<!-- DDL_SECTION:BEGIN -->

## DDL reference

### `app_insights_temp_applications`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.app_insights_temp_applications`(
  `applaunchid` string, 
  `start_delivery_timestamp` string, 
  `stop_delivery_timestamp` string, 
  `applaunchtime` string, 
  `appexittime` string, 
  `deviceid` string, 
  `devicetype` string, 
  `category` string, 
  `userprofileid` string, 
  `householdid` string, 
  `deviceversion` string, 
  `devicemode` string, 
  `launch_event` string, 
  `exit_event` string, 
  `appname` string, 
  `apptype` string, 
  `appid` string, 
  `appversion` string, 
  `applaunchpoint` string, 
  `swimlaneid` string, 
  `remotekeycode` string, 
  `serviceid` string, 
  `applaunchstatus` string, 
  `applaunchfailurereason` string, 
  `appexitstatus` string, 
  `appexitreason` string, 
  `exitstatus` string, 
  `launchstatus` string, 
  `subsystem` string, 
  `ingest_timestamp` string, 
  `deeplinkurl` string)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/warehouse/e6auj7k7_v1_applications'
TBLPROPERTIES (
  'has_encrypted_data'='false', 
  'transient_lastDdlTime'='1753269259')
```

### `app_insights_temp_downloads`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.app_insights_temp_downloads`(
  `api` string, 
  `apitype` string, 
  `busunitid` string, 
  `deviceid` string, 
  `devicetype` string, 
  `fcid` string, 
  `householdid` string, 
  `_timestamp` string, 
  `httpcode` string, 
  `downloadstatus` string, 
  `userprofileid` string, 
  `contentid` string, 
  `downloadid` string, 
  `contenttype` string, 
  `community` string, 
  `channelid` string, 
  `programtitle` string, 
  `src_timestamp` string, 
  `delivery_timestamp` string, 
  `timestamp` string)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/warehouse/e6auj7k7_v1_downloads'
TBLPROPERTIES (
  'has_encrypted_data'='false', 
  'transient_lastDdlTime'='1753269261')
```

### `app_insights_temp_sessions`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.app_insights_temp_sessions`(
  `sessionid` string, 
  `_timestamp` string, 
  `delivery_timestamp` string, 
  `starttime` string, 
  `endtime` string, 
  `householdid` string, 
  `deviceid` string, 
  `devicetype` string, 
  `sessiontype` string, 
  `duration` string, 
  `serviceid` string, 
  `ivpserviceid` string, 
  `broadcastserviceid` string, 
  `externalvodpackageid` string, 
  `servicedeliverytype` string, 
  `teardownreasontext` string, 
  `inhome` string, 
  `countrycode` string, 
  `gls_state` string, 
  `gls_city` string, 
  `providerid` string, 
  `userprofileid` string, 
  `ispname` string, 
  `offerkey` string, 
  `providerassetid` string, 
  `physicalcontentid` string, 
  `sessioncreatedfcid` string, 
  `networkstatus` string, 
  `networkname` string, 
  `event` string, 
  `dvrservicetype` string, 
  `recordstarttime` string, 
  `recordendtime` string, 
  `recordduration` string, 
  `count_event_progress` string, 
  `count_event_progress_fail` string, 
  `all_events` string, 
  `lastevent` string, 
  `firstevent` string, 
  `sessionduration` bigint, 
  `sessiondurationms` double, 
  `stat` string, 
  `result` string, 
  `starttime_ts` timestamp, 
  `recordstarttime_ts` timestamp, 
  `recordendtime_ts` timestamp, 
  `endtime_ts` timestamp, 
  `timestamp` timestamp, 
  `delivery_timestamp_ts` timestamp, 
  `recordduration_float` float, 
  `creationtime` string, 
  `externalteardownreason` string, 
  `src_timestamp` string)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/backup_source/sessions/e6auj7k7_v1_sessions'
TBLPROPERTIES (
  'spark.sql.create.version'='2.4.0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.numParts'='1', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema.part.0'='{\"type\":\"struct\",\"fields\":[{\"name\":\"sessionid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"_timestamp\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"delivery_timestamp\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"starttime\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"endtime\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"householdid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devicetype\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"sessiontype\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"duration\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"serviceid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ivpserviceid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"broadcastserviceid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"externalvodpackageid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"servicedeliverytype\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"teardownreasontext\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"inhome\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"countrycode\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"gls_state\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"gls_city\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"providerid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"userprofileid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ispname\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"offerkey\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"providerassetid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"physicalcontentid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"sessioncreatedfcid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"networkstatus\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"networkname\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"dvrservicetype\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"recordstarttime\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"recordendtime\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"recordduration\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"count_event_progress\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"count_event_progress_fail\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"all_events\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"lastevent\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"firstevent\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"sessionduration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"sessiondurationms\",\"type\":\"double\",\"nullable\":true,\"metadata\":{}},{\"name\":\"stat\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"result\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"starttime_ts\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"recordstarttime_ts\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"recordendtime_ts\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"endtime_ts\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"delivery_timestamp_ts\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"recordduration_float\",\"type\":\"float\",\"nullable\":true,\"metadata\":{}},{\"name\":\"creationtime\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"externalteardownreason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"src_timestamp\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted', 
  'transient_lastDdlTime'='1753269260')
```

### `channel_ranks`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.channel_ranks`(
  `viewing_date` date, 
  `device_type` string, 
  `session_type` string, 
  `channel` string, 
  `guest_mode` boolean, 
  `channel_rank` string, 
  `devices` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/channel_ranks') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/channel_ranks'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"viewing_date\",\"type\":\"date\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"Channel\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"Channel_Rank\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"Devices\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `country_data`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.country_data`(
  `country_code` varchar(2), 
  `country` varchar(44))
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/ccl-streaming/country_data/tables/0015f80c-fa0e-4447-ba88-01351dfe1eff'
TBLPROPERTIES (
  'auto.purge'='false', 
  'has_encrypted_data'='false', 
  'numFiles'='-1', 
  'parquet.compression'='SNAPPY', 
  'totalSize'='-1', 
  'transactional'='false', 
  'trino_query_id'='20260705_051609_00025_khi88', 
  'trino_version'='0.215-24607-gdd3e75d')
```

### `device_attributes`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.device_attributes`(
  `clientid` string, 
  `device_id` string, 
  `user_id` string, 
  `deviceos` string, 
  `devicename` string, 
  `countrycode` string, 
  `cohort` string, 
  `deviceclass` string, 
  `appversion` string, 
  `attribute_name` string, 
  `attribute_value` string, 
  `guest_mode` boolean, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/ccl-streaming/device_attributes') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/ccl-streaming/device_attributes'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"clientId\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceOs\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceName\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"countryCode\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"cohort\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceClass\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"appVersion\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"attribute_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"attribute_value\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted', 
  'transient_lastDdlTime'='1783041687')
```

### `device_data`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.device_data`(
  `clientid` string, 
  `device_id` string, 
  `user_id` string, 
  `deviceos` string, 
  `devicename` string, 
  `countrycode` string, 
  `cohort` string, 
  `deviceclass` string, 
  `appversion` string, 
  `guest_mode` boolean, 
  `ingest_timestamp` timestamp)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/ccl-streaming/device_data') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/ccl-streaming/device_data'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"clientId\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceOs\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceName\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"countryCode\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"cohort\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceClass\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"appVersion\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}}]}', 
  'transient_lastDdlTime'='1788773426')
```

### `device_data_view_trino`

```sql
CREATE VIEW `unified_e6auj7k7.device_data_view_trino` AS /* Presto View */
```

### `e6auj7k7_ccl_debug_events`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.e6auj7k7_ccl_debug_events`(
  `datetime` string COMMENT 'from deserializer', 
  `messageid` string COMMENT 'from deserializer', 
  `clibversion` string COMMENT 'from deserializer', 
  `clientid` string COMMENT 'from deserializer', 
  `eventclass` string COMMENT 'from deserializer', 
  `eventid` string COMMENT 'from deserializer', 
  `eventdata` string COMMENT 'from deserializer')
ROW FORMAT SERDE 
  'org.openx.data.jsonserde.JsonSerDe' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.mapred.TextInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/raw_source/source/2026/09'
TBLPROPERTIES (
  'transient_lastDdlTime'='1788303747')
```

### `e6auj7k7_ccl_debug_events_aug26`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.e6auj7k7_ccl_debug_events_aug26`(
  `datetime` string COMMENT 'from deserializer', 
  `messageid` string COMMENT 'from deserializer', 
  `clibversion` string COMMENT 'from deserializer', 
  `clientid` string COMMENT 'from deserializer', 
  `eventclass` string COMMENT 'from deserializer', 
  `eventid` string COMMENT 'from deserializer', 
  `eventdata` string COMMENT 'from deserializer')
ROW FORMAT SERDE 
  'org.openx.data.jsonserde.JsonSerDe' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.mapred.TextInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/raw_source/source/2026/08'
TBLPROPERTIES (
  'transient_lastDdlTime'='1788234022')
```

### `fact_applications`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.fact_applications`(
  `uid` string, 
  `device_id` string, 
  `user_id` string, 
  `device_group` string, 
  `device_type` string, 
  `app_name` string, 
  `duration_seconds_uncapped` bigint, 
  `duration_seconds` bigint, 
  `app_launch_point` string, 
  `event_start_uncapped` timestamp, 
  `event_start` timestamp, 
  `event_end_uncapped` timestamp, 
  `event_end` timestamp, 
  `event_start_tz` string, 
  `event_end_tz` string, 
  `local_timezone` string, 
  `app_status` string, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/fact_tables/fact_applications'
TBLPROPERTIES (
  'has_encrypted_data'='false', 
  'transient_lastDdlTime'='1753269187')
```

### `fact_downloads`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.fact_downloads`(
  `user_id` string, 
  `device_id` string, 
  `title` string, 
  `genres` string, 
  `top_genres` string, 
  `session_type` string, 
  `device_group` string, 
  `device_type` string, 
  `duration_seconds` bigint, 
  `event_start` timestamp, 
  `event_end` timestamp, 
  `event_start_tz` string, 
  `event_end_tz` string, 
  `local_timezone` string, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/fact_tables/fact_downloads'
TBLPROPERTIES (
  'has_encrypted_data'='false', 
  'transient_lastDdlTime'='1753269188')
```

### `fact_navigation_interactions`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.fact_navigation_interactions`(
  `user_id` string, 
  `device_id` string, 
  `device_type` string, 
  `uid` string, 
  `navigation_start_time` timestamp, 
  `navigation_end_time` timestamp, 
  `nav_event_time` timestamp, 
  `nav_step_num` bigint, 
  `nav_step_total` bigint, 
  `nav_start_event` boolean, 
  `nav_end_event` boolean, 
  `start_reason` string, 
  `end_reason` string, 
  `event_type` string, 
  `event` string, 
  `event_code` string, 
  `event_source` string, 
  `event_source_ex` string, 
  `event_source_ex_name` string, 
  `source_name` string, 
  `event_details` string, 
  `screen_count` bigint, 
  `screen_view_duration` bigint, 
  `guest_mode` boolean, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/fact_navigation_interactions') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/fact_navigation_interactions'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"uid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_start_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_end_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"nav_event_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"nav_step_num\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"nav_step_total\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"nav_start_event\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"nav_end_event\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"start_reason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"end_reason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_code\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_source\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_source_ex\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_source_ex_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"source_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_details\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"screen_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"screen_view_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `fact_navigation_journeys`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.fact_navigation_journeys`(
  `user_id` string, 
  `device_id` string, 
  `uid` string, 
  `navigation_start_time` timestamp, 
  `navigation_end_time` timestamp, 
  `duration_seconds` bigint, 
  `step_count` bigint, 
  `screen_count` bigint, 
  `start_reason` string, 
  `end_reason` string, 
  `next_viewing_source_name` string, 
  `device_type` string, 
  `next_viewing_session_id` string, 
  `next_viewing_session_type` string, 
  `next_viewing_content` string, 
  `next_viewing_content_source` string, 
  `next_viewing_session_duration` bigint, 
  `back_to_viewing_session_id` string, 
  `back_to_viewing_session_x1_duration` bigint, 
  `prev_viewing_session_id` string, 
  `prev_viewing_session_type` string, 
  `prev_viewing_session_duration` bigint, 
  `guest_mode` boolean, 
  `ingest_timestamp` timestamp, 
  `journey_type` string, 
  `lead_to_view` boolean)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/fact_navigation_journeys') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/fact_navigation_journeys'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"uid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_start_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_end_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"duration_seconds\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"step_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"screen_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"start_reason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"end_reason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_source_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_session_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_content\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_content_source\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_session_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"back_to_viewing_session_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"back_to_viewing_session_x1_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"prev_viewing_session_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"prev_viewing_session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"prev_viewing_session_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"journey_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"lead_to_view\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `fact_navigation_steps`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.fact_navigation_steps`(
  `uid` string, 
  `ingest_timestamp` timestamp, 
  `day_id` int, 
  `hour_id` int, 
  `user_id` string, 
  `device_id` string, 
  `device_type` string, 
  `event` string, 
  `event_code` string, 
  `event_type` string, 
  `event_source` string, 
  `event_source_ex` string, 
  `event_source_ex_name` string, 
  `source_name` string, 
  `event_details` string, 
  `event_ts` timestamp, 
  `event_tz` timestamp, 
  `local_timezone` string, 
  `guest_mode` boolean)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/fact_navigation_steps') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/fact_navigation_steps'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"uid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"day_id\",\"type\":\"integer\",\"nullable\":true,\"metadata\":{}},{\"name\":\"hour_id\",\"type\":\"integer\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_code\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_source\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_source_ex\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_source_ex_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"source_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_details\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_ts\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_tz\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"local_timezone\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `fact_navigation_to_features`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.fact_navigation_to_features`(
  `uid` string, 
  `user_id` string, 
  `device_id` string, 
  `device_type` string, 
  `navigation_start_time` timestamp, 
  `navigation_end_time` timestamp, 
  `hour` int, 
  `navigation_start_time_tz` string, 
  `navigation_end_time_tz` string, 
  `source_name` string, 
  `duration_seconds` bigint, 
  `next_viewing_session_id` string, 
  `next_viewing_session_type` string, 
  `next_viewing_session_duration` bigint, 
  `next_viewing_content` string, 
  `next_viewing_content_source` string, 
  `guest_mode` boolean, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/fact_navigation_to_features') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/fact_navigation_to_features'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"uid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_start_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_end_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"hour\",\"type\":\"integer\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_start_time_tz\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_end_time_tz\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"source_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"duration_seconds\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_session_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_session_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_content\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_content_source\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `fact_sessions`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.fact_sessions`(
  `uid` string, 
  `day_id` int, 
  `hour_id` int, 
  `user_id` string, 
  `user_details` string, 
  `device_id` string, 
  `parent_session_id` string, 
  `device_type` string, 
  `device_desc` string, 
  `country` string, 
  `cohort` string, 
  `state` string, 
  `city` string, 
  `event_type` string, 
  `event_start` timestamp, 
  `event_end` timestamp, 
  `event_start_tz` timestamp, 
  `event_end_tz` timestamp, 
  `local_timezone` string, 
  `duration_seconds` bigint, 
  `content_type` string, 
  `content` string, 
  `content_id` string, 
  `content_details` string, 
  `content_desc` string, 
  `content_desc_ex` string, 
  `content_source` string, 
  `content_source_desc` string, 
  `ingest_timestamp` timestamp, 
  `user_region` string, 
  `user_entitlements` string, 
  `guest_mode` boolean)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/fact_sessions') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/fact_sessions'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"uid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"day_id\",\"type\":\"integer\",\"nullable\":true,\"metadata\":{}},{\"name\":\"hour_id\",\"type\":\"integer\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_details\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"parent_session_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_desc\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"country\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"cohort\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"state\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"city\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_start\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_end\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_start_tz\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_end_tz\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"local_timezone\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"duration_seconds\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_details\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_desc\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_desc_ex\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_source\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_source_desc\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_region\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_entitlements\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `fact_sessions_export_20260124`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.fact_sessions_export_20260124`(
  `uid` string COMMENT 'from deserializer', 
  `day_id` string COMMENT 'from deserializer', 
  `hour_id` string COMMENT 'from deserializer', 
  `user_id` string COMMENT 'from deserializer', 
  `device_id` string COMMENT 'from deserializer', 
  `device_type` string COMMENT 'from deserializer', 
  `device_desc` string COMMENT 'from deserializer', 
  `country` string COMMENT 'from deserializer', 
  `state` string COMMENT 'from deserializer', 
  `city` string COMMENT 'from deserializer', 
  `event_type` string COMMENT 'from deserializer', 
  `event_start` string COMMENT 'from deserializer', 
  `event_end` string COMMENT 'from deserializer', 
  `event_start_tz` string COMMENT 'from deserializer', 
  `event_end_tz` string COMMENT 'from deserializer', 
  `local_timezone` string COMMENT 'from deserializer', 
  `duration_seconds` string COMMENT 'from deserializer', 
  `content_type` string COMMENT 'from deserializer', 
  `content` string COMMENT 'from deserializer', 
  `content_id` string COMMENT 'from deserializer', 
  `content_details` string COMMENT 'from deserializer', 
  `content_desc` string COMMENT 'from deserializer', 
  `content_desc_ex` string COMMENT 'from deserializer', 
  `content_source` string COMMENT 'from deserializer', 
  `content_source_desc` string COMMENT 'from deserializer', 
  `ingest_timestamp` string COMMENT 'from deserializer', 
  `user_region` string COMMENT 'from deserializer', 
  `user_details` string COMMENT 'from deserializer', 
  `cohort` string COMMENT 'from deserializer')
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.serde2.OpenCSVSerde' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.mapred.TextInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/temp_reports/20260124/fact_sessions_export'
TBLPROPERTIES (
  'STATS_GENERATED_VIA_STATS_TASK'='workaround for potential lack of HIVE-12730', 
  'auto.purge'='false', 
  'numFiles'='0', 
  'numRows'='0', 
  'presto_query_id'='20260125_130240_00139_wc373', 
  'presto_version'='380-e.1', 
  'rawDataSize'='0', 
  'skip.header.line.count'='1', 
  'totalSize'='0', 
  'transactional'='false')
```

### `fact_ui_sessions`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.fact_ui_sessions`(
  `uid` string, 
  `device_id` string, 
  `user_id` string, 
  `device_type` string, 
  `event_start` timestamp, 
  `event_end` timestamp, 
  `country` string, 
  `cohort` string, 
  `duration_seconds` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/fact_ui_sessions') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/fact_ui_sessions'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"uid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_start\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_end\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"country\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"cohort\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"duration_seconds\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `ip_data`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.ip_data`(
  `clientid` string, 
  `device_id` string, 
  `user_id` string, 
  `ipaddress` string, 
  `guest_mode` boolean, 
  `ingest_timestamp` timestamp)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/ccl-streaming/ip_data') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/ccl-streaming/ip_data'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"clientId\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ipAddress\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}}]}', 
  'transient_lastDdlTime'='1788774030')
```

### `rep_channelhour_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_channelhour_agg`(
  `calendar_date` date, 
  `device_type` string, 
  `session_type` string, 
  `sessionhour` string, 
  `channel_name` string, 
  `country` string, 
  `cohort` string, 
  `guest_mode` boolean, 
  `session_count` bigint, 
  `session_duration` bigint, 
  `households` bigint, 
  `devices` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_channelhour_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_channelhour_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"calendar_date\",\"type\":\"date\",\"nullable\":true,\"metadata\":{\"__metadata_col\":true,\"__supports_qualified_star\":true}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{\"__metadata_col\":true,\"__supports_qualified_star\":true}},{\"name\":\"session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{\"__metadata_col\":true,\"__supports_qualified_star\":true}},{\"name\":\"sessionHour\",\"type\":\"string\",\"nullable\":true,\"metadata\":{\"__metadata_col\":true,\"__supports_qualified_star\":true}},{\"name\":\"channel_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{\"__metadata_col\":true,\"__supports_qualified_star\":true}},{\"name\":\"country\",\"type\":\"string\",\"nullable\":true,\"metadata\":{\"__metadata_col\":true,\"__supports_qualified_star\":true}},{\"name\":\"cohort\",\"type\":\"string\",\"nullable\":true,\"metadata\":{\"__metadata_col\":true,\"__supports_qualified_star\":true}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{\"__metadata_col\":true,\"__supports_qualified_star\":true}},{\"name\":\"session_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"households\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devices\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_channelhour_agg_export_20260124`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_channelhour_agg_export_20260124`(
  `calendar_date` string COMMENT 'from deserializer', 
  `device_type` string COMMENT 'from deserializer', 
  `session_type` string COMMENT 'from deserializer', 
  `sessionhour` string COMMENT 'from deserializer', 
  `channel_name` string COMMENT 'from deserializer', 
  `session_count` string COMMENT 'from deserializer', 
  `session_duration` string COMMENT 'from deserializer', 
  `households` string COMMENT 'from deserializer', 
  `devices` string COMMENT 'from deserializer', 
  `country` string COMMENT 'from deserializer', 
  `cohort` string COMMENT 'from deserializer')
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.serde2.OpenCSVSerde' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.mapred.TextInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/temp_reports/20260124/rep_channelhour_agg_export'
TBLPROPERTIES (
  'STATS_GENERATED_VIA_STATS_TASK'='workaround for potential lack of HIVE-12730', 
  'auto.purge'='false', 
  'numFiles'='0', 
  'numRows'='0', 
  'presto_query_id'='20260125_130233_00115_wc373', 
  'presto_version'='380-e.1', 
  'rawDataSize'='0', 
  'skip.header.line.count'='1', 
  'totalSize'='0', 
  'transactional'='false')
```

### `rep_daily_content_agg_details`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_daily_content_agg_details`(
  `calendar_date` date, 
  `device_group` string, 
  `device_type` string, 
  `session_type` string, 
  `channel` string, 
  `program_title` string, 
  `program_genres` string, 
  `program_audiolang` string, 
  `program_subtitlelang` string, 
  `country` string, 
  `cohort` string, 
  `guest_mode` boolean, 
  `session_count` bigint, 
  `session_duration` bigint, 
  `households` bigint, 
  `devices` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_daily_content_agg_details') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_daily_content_agg_details'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"calendar_date\",\"type\":\"date\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_group\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"channel\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"program_title\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"program_genres\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"program_audiolang\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"program_subtitlelang\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"country\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"cohort\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"households\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devices\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_daily_device_1d_base_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_daily_device_1d_base_agg`(
  `device_type` string, 
  `country` string, 
  `cohort` string, 
  `guest_mode` boolean, 
  `devices_1d` bigint, 
  `households_1d` bigint, 
  `viewing_date` date, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_daily_device_1d_base_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_daily_device_1d_base_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"country\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"cohort\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devices_1d\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"households_1d\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"viewing_date\",\"type\":\"date\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_daily_device_30d_base_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_daily_device_30d_base_agg`(
  `viewing_date` date, 
  `device_type` string, 
  `country` string, 
  `cohort` string, 
  `guest_mode` boolean, 
  `devices_30d` bigint, 
  `households_30d` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_daily_device_30d_base_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_daily_device_30d_base_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"viewing_date\",\"type\":\"date\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"country\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"cohort\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devices_30d\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"households_30d\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_daily_device_7d_base_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_daily_device_7d_base_agg`(
  `device_type` string, 
  `country` string, 
  `cohort` string, 
  `guest_mode` boolean, 
  `devices_7d` bigint, 
  `households_7d` bigint, 
  `viewing_date` date, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_daily_device_7d_base_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_daily_device_7d_base_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"country\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"cohort\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devices_7d\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"households_7d\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"viewing_date\",\"type\":\"date\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_daily_device_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_daily_device_agg`(
  `calendar_date` date, 
  `device_group` string, 
  `device_type` string, 
  `guest_mode` boolean, 
  `session_count` bigint, 
  `session_duration` bigint, 
  `households` bigint, 
  `devices` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_daily_device_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_daily_device_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"calendar_date\",\"type\":\"date\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_group\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"households\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devices\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_daily_device_agg_export_20260124`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_daily_device_agg_export_20260124`(
  `calendar_date` string COMMENT 'from deserializer', 
  `device_type` string COMMENT 'from deserializer', 
  `device_group` string COMMENT 'from deserializer', 
  `session_count` string COMMENT 'from deserializer', 
  `session_duration` string COMMENT 'from deserializer', 
  `households` string COMMENT 'from deserializer', 
  `devices` string COMMENT 'from deserializer')
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.serde2.OpenCSVSerde' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.mapred.TextInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/temp_reports/20260124/rep_daily_device_agg_export'
TBLPROPERTIES (
  'STATS_GENERATED_VIA_STATS_TASK'='workaround for potential lack of HIVE-12730', 
  'auto.purge'='false', 
  'numFiles'='0', 
  'numRows'='0', 
  'presto_query_id'='20260125_130238_00131_wc373', 
  'presto_version'='380-e.1', 
  'rawDataSize'='0', 
  'skip.header.line.count'='1', 
  'totalSize'='0', 
  'transactional'='false')
```

### `rep_daily_feature_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_daily_feature_agg`(
  `household_id` string, 
  `device_type` string, 
  `feature` string, 
  `session_type` string, 
  `guest_mode` boolean, 
  `return_user` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_daily_feature_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_daily_feature_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"household_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"feature\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"return_user\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_daily_session_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_daily_session_agg`(
  `calendar_date` date, 
  `device_type` string, 
  `session_type` string, 
  `guest_mode` boolean, 
  `session_count` bigint, 
  `session_duration` bigint, 
  `households` bigint, 
  `devices` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_daily_session_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_daily_session_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"calendar_date\",\"type\":\"date\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"households\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devices\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_daily_session_agg_export_20260124`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_daily_session_agg_export_20260124`(
  `calendar_date` string COMMENT 'from deserializer', 
  `device_type` string COMMENT 'from deserializer', 
  `session_type` string COMMENT 'from deserializer', 
  `session_count` string COMMENT 'from deserializer', 
  `session_duration` string COMMENT 'from deserializer', 
  `households` string COMMENT 'from deserializer', 
  `devices` string COMMENT 'from deserializer')
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.serde2.OpenCSVSerde' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.mapred.TextInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/temp_reports/20260124/rep_daily_session_agg_export'
TBLPROPERTIES (
  'STATS_GENERATED_VIA_STATS_TASK'='workaround for potential lack of HIVE-12730', 
  'auto.purge'='false', 
  'numFiles'='0', 
  'numRows'='0', 
  'presto_query_id'='20260125_130242_00159_wc373', 
  'presto_version'='380-e.1', 
  'rawDataSize'='0', 
  'skip.header.line.count'='1', 
  'totalSize'='0', 
  'transactional'='false')
```

### `rep_device_attributes_daily_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_device_attributes_daily_agg`(
  `processing_date` string, 
  `deviceclass` string, 
  `appversion` string, 
  `attribute_name` string, 
  `attribute_value` string, 
  `unique_device_count` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_device_attributes_daily_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_device_attributes_daily_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"processing_date\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceClass\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"appVersion\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"attribute_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"attribute_value\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"unique_device_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_devices_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_devices_agg`(
  `viewing_date` date, 
  `time_period` string, 
  `device_type` string, 
  `device_order` int, 
  `guest_mode` boolean, 
  `households_dist` bigint, 
  `devices_dist` bigint, 
  `duration_dist` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_devices_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_devices_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"viewing_date\",\"type\":\"date\",\"nullable\":true,\"metadata\":{}},{\"name\":\"Time_Period\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_order\",\"type\":\"integer\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"households_dist\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devices_dist\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"duration_dist\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_devices_agg_export_20260124`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_devices_agg_export_20260124`(
  `viewing_date` string COMMENT 'from deserializer', 
  `time_period` string COMMENT 'from deserializer', 
  `device_type` string COMMENT 'from deserializer', 
  `device_order` string COMMENT 'from deserializer', 
  `households_dist` string COMMENT 'from deserializer', 
  `devices_dist` string COMMENT 'from deserializer', 
  `duration_dist` string COMMENT 'from deserializer')
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.serde2.OpenCSVSerde' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.mapred.TextInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/temp_reports/20260124/rep_devices_agg_export'
TBLPROPERTIES (
  'STATS_GENERATED_VIA_STATS_TASK'='workaround for potential lack of HIVE-12730', 
  'auto.purge'='false', 
  'numFiles'='1', 
  'numRows'='117', 
  'presto_query_id'='20260125_130242_00170_wc373', 
  'presto_version'='380-e.1', 
  'rawDataSize'='8231', 
  'skip.header.line.count'='1', 
  'totalSize'='943', 
  'transactional'='false')
```

### `rep_hourly_journey_aggregation`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_hourly_journey_aggregation`(
  `device_type` string, 
  `hour` int, 
  `lead_to_view` boolean, 
  `next_viewing_session_type` string, 
  `next_viewing_content_source` string, 
  `next_viewing_content` string, 
  `journey_type` string, 
  `guest_mode` boolean, 
  `total_seconds` bigint, 
  `total_steps` bigint, 
  `devices` bigint, 
  `users` bigint, 
  `total_journeys` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_hourly_journey_aggregation') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_hourly_journey_aggregation'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"hour\",\"type\":\"integer\",\"nullable\":true,\"metadata\":{}},{\"name\":\"lead_to_view\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_content_source\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_content\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"journey_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"total_seconds\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"total_steps\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devices\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"users\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"total_journeys\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_hourly_screens_aggregation`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_hourly_screens_aggregation`(
  `device_type` string, 
  `screen` string, 
  `hour` int, 
  `guest_mode` boolean, 
  `hits` bigint, 
  `duration_seconds` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_hourly_screens_aggregation') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_hourly_screens_aggregation'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"screen\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"hour\",\"type\":\"integer\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"hits\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"duration_seconds\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_hourly_swimlane_aggregation`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_hourly_swimlane_aggregation`(
  `device_type` string, 
  `swimlane` string, 
  `hour` int, 
  `guest_mode` boolean, 
  `user_actions` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_hourly_swimlane_aggregation') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_hourly_swimlane_aggregation'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"swimlane\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"hour\",\"type\":\"integer\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_actions\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_household_device_base_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_household_device_base_agg`(
  `guest_mode` boolean, 
  `num_households` bigint, 
  `num_devices` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_household_device_base_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_household_device_base_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"num_households\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"num_devices\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_mau_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_mau_agg`(
  `monthnum` string, 
  `guest_mode` boolean, 
  `households` bigint, 
  `devices` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_mau_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_mau_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"monthnum\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"households\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devices\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_mtd_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_mtd_agg`(
  `month` string, 
  `monthnum` string, 
  `completemonth` int, 
  `device_group` string, 
  `guest_mode` boolean, 
  `mtd_households` bigint, 
  `mtd_devices` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_mtd_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_mtd_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"Month\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"MonthNum\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"CompleteMonth\",\"type\":\"integer\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_group\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"mtd_households\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"mtd_devices\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_op_concurrency_insights_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_op_concurrency_insights_agg`(
  `content_type` string, 
  `device_type` string, 
  `device_desc` string, 
  `guest_mode` boolean, 
  `session_minute` timestamp, 
  `session_hour` timestamp, 
  `viewing_seconds` bigint, 
  `buffering_seconds` bigint, 
  `minute_device_count` bigint, 
  `hour_device_count` bigint, 
  `concurrent_play_starts` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_op_concurrency_insights_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_op_concurrency_insights_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"content_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_desc\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_minute\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_hour\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"viewing_seconds\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"buffering_seconds\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"minute_device_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"hour_device_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"concurrent_play_starts\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_op_daily_active_dev_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_op_daily_active_dev_agg`(
  `device_type` string, 
  `content_type` string, 
  `device_desc` string, 
  `device_id` string, 
  `guest_mode` boolean, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_op_daily_active_dev_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_op_daily_active_dev_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_desc\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_op_insights_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_op_insights_agg`(
  `device_type` string, 
  `content_type` string, 
  `device_desc` string, 
  `content` string, 
  `content_source` string, 
  `guest_mode` boolean, 
  `session_count` bigint, 
  `request_view_count` bigint, 
  `play_count` bigint, 
  `request_ends_with_play_count` bigint, 
  `player_error_count` bigint, 
  `exit_before_play_count` bigint, 
  `request_ended_with_error_count` bigint, 
  `sessions_ended_due_to_buffering_count` bigint, 
  `buffering_duration_seconds` bigint, 
  `viewing_duration_seconds` bigint, 
  `buffering_sessions_count` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_op_insights_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_op_insights_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_desc\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_source\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"request_view_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"play_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"request_ends_with_play_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"player_error_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"exit_before_play_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"request_ended_with_error_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"sessions_ended_due_to_buffering_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"buffering_duration_seconds\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"viewing_duration_seconds\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"buffering_sessions_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_top_channel_device_agg`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_top_channel_device_agg`(
  `viewing_date` date, 
  `timeperiod` string, 
  `device_type` string, 
  `session_type` string, 
  `channel` string, 
  `channel_rank` string, 
  `guest_mode` boolean, 
  `devices` bigint, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/rep_top_channel_device_agg') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/rep_top_channel_device_agg'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"viewing_date\",\"type\":\"date\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timeperiod\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"Channel\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"Channel_Rank\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"Devices\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted')
```

### `rep_top_channel_device_agg_export_20260426`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.rep_top_channel_device_agg_export_20260426`(
  `viewing_date` string COMMENT 'from deserializer', 
  `timeperiod` string COMMENT 'from deserializer', 
  `device_type` string COMMENT 'from deserializer', 
  `session_type` string COMMENT 'from deserializer', 
  `channel` string COMMENT 'from deserializer', 
  `channel_rank` string COMMENT 'from deserializer', 
  `devices` string COMMENT 'from deserializer')
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.serde2.OpenCSVSerde' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.mapred.TextInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/temp_reports/20260426/rep_top_channel_device_agg_export/'
TBLPROPERTIES (
  'auto.purge'='false', 
  'numFiles'='1', 
  'numRows'='7', 
  'rawDataSize'='548', 
  'skip.header.line.count'='1', 
  'totalSize'='182', 
  'transactional'='false', 
  'trino_query_id'='20260427_130416_00291_bbhgn', 
  'trino_version'='479-e.1')
```

### `temp_device_data_table`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.temp_device_data_table`(
  `clientid` string, 
  `device_id` string, 
  `user_id` string, 
  `guest_mode` boolean, 
  `ingest_timestamp` timestamp, 
  `deviceclass` string, 
  `deviceos` string, 
  `devicename` string, 
  `countrycode` string, 
  `cohort` string, 
  `appversion` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/ccl-streaming/temp_device_data') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/ccl-streaming/temp_device_data'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"clientId\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceClass\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceOs\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceName\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"countryCode\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"cohort\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"appVersion\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'transient_lastDdlTime'='1788774021')
```

### `temp_ip_data_table`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.temp_ip_data_table`(
  `clientid` string, 
  `device_id` string, 
  `user_id` string, 
  `guest_mode` boolean, 
  `ingest_timestamp` timestamp, 
  `ipaddress` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/ccl-streaming/temp_ip_data') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/ccl-streaming/temp_ip_data'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"clientId\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ipAddress\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'transient_lastDdlTime'='1788774028')
```

### `temp_linked_navigation_sessions`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.temp_linked_navigation_sessions`(
  `user_id` string, 
  `device_id` string, 
  `uid` string, 
  `navigation_start_time` timestamp, 
  `navigation_end_time` timestamp, 
  `duration_seconds` bigint, 
  `step_count` bigint, 
  `screen_count` bigint, 
  `start_reason` string, 
  `end_reason` string, 
  `next_viewing_source_name` string, 
  `device_type` string, 
  `next_viewing_session_id` string, 
  `next_viewing_session_type` string, 
  `next_viewing_content` string, 
  `next_viewing_content_source` string, 
  `next_viewing_session_duration` bigint, 
  `back_to_viewing_session_id` string, 
  `back_to_viewing_session_x1_duration` bigint, 
  `prev_viewing_session_id` string, 
  `prev_viewing_session_type` string, 
  `prev_viewing_session_duration` bigint, 
  `guest_mode` boolean, 
  `timestamp_formatted` string, 
  `ingest_timestamp` timestamp)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/temp_linked_navigation_sessions') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/temp_linked_navigation_sessions'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"uid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_start_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_end_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"duration_seconds\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"step_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"screen_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"start_reason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"end_reason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_source_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_session_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_content\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_content_source\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"next_viewing_session_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"back_to_viewing_session_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"back_to_viewing_session_x1_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"prev_viewing_session_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"prev_viewing_session_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"prev_viewing_session_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}}]}', 
  'transient_lastDdlTime'='1788746802')
```

### `temp_navigation_sessions`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.temp_navigation_sessions`(
  `user_id` string, 
  `device_id` string, 
  `uid` string, 
  `navigation_start_time` timestamp, 
  `navigation_end_time` timestamp, 
  `step_count` bigint, 
  `screen_count` bigint, 
  `start_reason` string, 
  `end_reason` string, 
  `source_name` string, 
  `device_type` string, 
  `duration_ms` bigint, 
  `guest_mode` boolean, 
  `timestamp_formatted` string, 
  `ingest_timestamp` timestamp)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/temp_navigation_sessions') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/temp_navigation_sessions'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"uid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_start_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_end_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"step_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"screen_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"start_reason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"end_reason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"source_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"duration_ms\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}}]}', 
  'transient_lastDdlTime'='1788746427')
```

### `temp_navigation_steps`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.temp_navigation_steps`(
  `user_id` string, 
  `device_id` string, 
  `device_type` string, 
  `uid` string, 
  `navigation_start_time` timestamp, 
  `navigation_end_time` timestamp, 
  `nav_event_time` timestamp, 
  `nav_step_num` bigint, 
  `nav_step_total` bigint, 
  `nav_start_event` boolean, 
  `nav_end_event` boolean, 
  `start_reason` string, 
  `end_reason` string, 
  `event_type` string, 
  `event` string, 
  `event_code` string, 
  `event_source` string, 
  `event_source_ex` string, 
  `event_source_ex_name` string, 
  `source_name` string, 
  `event_details` string, 
  `screen_count` bigint, 
  `screen_view_duration` bigint, 
  `guest_mode` boolean, 
  `timestamp_formatted` string, 
  `ingest_timestamp` timestamp)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/aggregations/temp_navigation_steps') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/aggregations/temp_navigation_steps'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"uid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_start_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"navigation_end_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"nav_event_time\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"nav_step_num\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"nav_step_total\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"nav_start_event\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"nav_end_event\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"start_reason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"end_reason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_code\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_source\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_source_ex\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_source_ex_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"source_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_details\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"screen_count\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"screen_view_duration\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}}]}', 
  'transient_lastDdlTime'='1788746147')
```

### `unified_applications`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.unified_applications`(
  `applaunchid` string, 
  `deviceid` string, 
  `householdid` string, 
  `applaunchtime` string, 
  `appexittime` string, 
  `appid` string, 
  `launch_event` string, 
  `exit_event` string, 
  `swimlaneid` string, 
  `deeplinkurl` string, 
  `devicetype` string, 
  `start_delivery_timestamp` string, 
  `stop_delivery_timestamp` string, 
  `category` string, 
  `userprofileid` string, 
  `deviceversion` string, 
  `devicemode` string, 
  `appname` string, 
  `apptype` string, 
  `appversion` string, 
  `remotekeycode` string, 
  `serviceid` string, 
  `applaunchpoint` string, 
  `applaunchstatus` string, 
  `applaunchfailurereason` string, 
  `appexitstatus` string, 
  `appexitreason` string, 
  `subsystem` string, 
  `launchstatus` string, 
  `exitstatus` string, 
  `ingest_timestamp` string)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/ccl-streaming/applications') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/ccl-streaming/applications'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"applaunchid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"householdid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"applaunchtime\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"appexittime\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"appid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"launch_event\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"exit_event\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"swimlaneid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deeplinkurl\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devicetype\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"start_delivery_timestamp\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"stop_delivery_timestamp\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"category\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"userprofileid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"deviceversion\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"devicemode\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"appname\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"apptype\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"appversion\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"remotekeycode\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"serviceid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"applaunchpoint\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"applaunchstatus\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"applaunchfailurereason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"appexitstatus\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"appexitreason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"subsystem\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"launchstatus\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"exitstatus\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted', 
  'transient_lastDdlTime'='1751541702')
```

### `unified_navigation_steps`

```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.unified_navigation_steps`(
  `uid` string, 
  `device_id` string, 
  `user_id` string, 
  `event_ts` timestamp, 
  `event` string, 
  `event_type` string, 
  `event_source` string, 
  `event_source_ex` string, 
  `event_details` string, 
  `event_code` string, 
  `state` string, 
  `device_type` string, 
  `guest_mode` boolean, 
  `source_name` string, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/ccl-streaming/navigation_steps') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/ccl-streaming/navigation_steps'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"uid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_ts\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_source\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_source_ex\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_details\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_code\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"state\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"source_name\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted', 
  'transient_lastDdlTime'='1783041548')
```

### `unified_sessions`

Known caveat: if you are using the registered per-session playback-outcome classification against this table, cross-check `knowledge/mtn-adoption-playback-outcome-classification-gap.md` for the VSF
misclassification gap before treating `INCOMPLETE_NO_DESTROY` as a clean bucket.


```sql
CREATE EXTERNAL TABLE `unified_e6auj7k7.unified_sessions`(
  `parent_session_id` string, 
  `device_id` string, 
  `user_id` string, 
  `event_type` string, 
  `event_start` timestamp, 
  `event_end` timestamp, 
  `content_type` string, 
  `content` string, 
  `content_id` string, 
  `content_desc` string, 
  `content_desc_ex` string, 
  `content_source` string, 
  `content_source_desc` string, 
  `endreason` string, 
  `audiolang` string, 
  `sublang` string, 
  `device_type` string, 
  `guest_mode` boolean, 
  `user_entitlements` string, 
  `ip_address` string, 
  `device_desc` string, 
  `cohort` string, 
  `country` string, 
  `uid` string, 
  `city` string, 
  `state` string, 
  `user_region` string, 
  `content_details` string, 
  `ingest_timestamp` timestamp)
PARTITIONED BY ( 
  `timestamp_formatted` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
WITH SERDEPROPERTIES ( 
  'path'='s3://clarissa-unified-e6auj7k7/ccl-streaming/sessions') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://clarissa-unified-e6auj7k7/ccl-streaming/sessions'
TBLPROPERTIES (
  'spark.sql.create.version'='3.2.1-amzn-0', 
  'spark.sql.partitionProvider'='catalog', 
  'spark.sql.sources.provider'='parquet', 
<!-- lint-ignore-length -->
  'spark.sql.sources.schema'='{\"type\":\"struct\",\"fields\":[{\"name\":\"parent_session_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_start\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"event_end\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_id\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_desc\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_desc_ex\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_source\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_source_desc\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"endReason\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"audioLang\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"subLang\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_type\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"guest_mode\",\"type\":\"boolean\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_entitlements\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ip_address\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"device_desc\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"cohort\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"country\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"uid\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"city\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"state\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"user_region\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"content_details\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}},{\"name\":\"ingest_timestamp\",\"type\":\"timestamp\",\"nullable\":true,\"metadata\":{}},{\"name\":\"timestamp_formatted\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}]}', 
  'spark.sql.sources.schema.numPartCols'='1', 
  'spark.sql.sources.schema.partCol.0'='timestamp_formatted', 
  'transient_lastDdlTime'='1783041477')
```

### `vw_top10_unique_content`

```sql
CREATE VIEW `unified_e6auj7k7.vw_top10_unique_content` AS /* Presto View */
```

<!-- DDL_SECTION:END -->

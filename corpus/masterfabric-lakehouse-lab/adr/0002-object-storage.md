# 0002. S3-compatible object storage, RustFS in the lab

- Status: Accepted
- Date: 2026-11-21

## Context

Enterprise lakehouses sit on HDFS (classic CDH), Apache Ozone (CDP Private Cloud) or a cloud
object store. Iceberg is designed for object storage: it never relies on rename or directory
listing for correctness. The lab needs something S3-compatible that runs in one container.

The original plan was MinIO. On the day this lab was built (November 2026) the MinIO
container images could not be pulled anonymously from the M4 Pro: `docker pull minio/minio`
returned `pull access denied ... repository does not exist` and `quay.io/minio/minio`
returned `401 UNAUTHORIZED`. A lab whose first command fails is not a lab.

## Options

| Option | For | Against |
|---|---|---|
| MinIO | Best known, rich console | Images not anonymously pullable at build time; AGPL server |
| **RustFS** | S3-compatible, single container, web console, Apache-2.0, accepts MinIO-style env vars | Younger project |
| SeaweedFS | Mature, S3 gateway, Apache-2.0 | No comparable bucket browser for the screenshots; more moving parts |
| Apache Ozone | The actual CDP Private Cloud object store, S3 gateway | Needs SCM + OM + datanodes + S3G: too heavy for a laptop lab |

## Decision

Use **RustFS 1.0.6** as the S3 endpoint (`s3` service, API on 127.0.0.1:19000, console on
127.0.0.1:19001). Iceberg talks to it through `S3FileIO` with path-style access.

## Consequences

- Nothing in the code is RustFS-specific: swapping in MinIO, Ozone's S3 gateway, Ceph RGW or
  AWS S3 is a change of endpoint and credentials in `.env` and `docker/`.
- The Spark image has no Hadoop `s3://` connector (Iceberg does not need one). Raw files are
  therefore read from a bind-mounted landing directory, and Iceberg's Hadoop-based orphan
  file action cannot list the bucket; the lab does the orphan scan through Iceberg FileIO
  instead (ADR 0007). On a CDP cluster both would use the cluster's HDFS/Ozone connector.

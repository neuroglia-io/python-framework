# Requirements

1. CML (Cisco Modeling Labs) Specifics
   What is the CML Worker API endpoint structure? (e.g., REST API base URL format)
   > Please read the references/cml_openapi.json for detailed API specifications.

What authentication method does CML use? (API tokens, OAuth, etc.)

> Please read the references/cml_openapi.json for detailed API specifications.

What are the specific API calls for:
Licensing a CML worker?

> Please read the references/cml_openapi.json for detailed API specifications.

Starting/stopping a CML worker?

> Please read the references/cml_openapi.json for detailed API specifications.

Getting CPU/Memory/Storage utilization?

> Please read the references/cml_openapi.json for detailed API specifications.

Provisioning a lab instance on the worker?

> Please read the references/cml_openapi.json for detailed API specifications.

2. AWS EC2 Provisioning Details
   What specific EC2 instance type(s) should be used? (e.g., t3.xlarge, m5.2xlarge)

> m5zn.metal

What's the workflow for the AMI? Do we:
Have a pre-configured CML AMI ID? yes (will be provided as env var)
Need to configure CML after EC2 launch? only license it once it is ready.

Storage requirements:
EBS volume size and type? io1
Additional volumes needed?
Networking requirements:
Should the LabWorker be in a specific VPC subnet? yes (will be provided as env var)
Public IP required or private only? public ip required
Specific security group rules? yes (will be provided as env var)

3. LabWorker Lifecycle States
   What states should a LabWorker go through? For example:

PENDING → Waiting to be provisioned
PROVISIONING_EC2 → Creating EC2 instance
EC2_READY → EC2 running, installing CML
STARTING → Starting CML services
READY_UNLICENSED → Ready to accept lab instance requests with less than 5 nodes
LICENSING → Applying CML license
UNLICENSING → Removing the CML license
READY → Ready to accept lab instance requests with full capacity
ACTIVE → Hosting lab instances
DRAINING → Not accepting new instances, finishing existing
STOPPING → Shutting down
TERMINATED → Cleaned up

1. Resource Capacity Management
   How do we determine LabWorker capacity? based on resource limits defined in CML API and based on resource requested
   Fixed capacity per worker type? no
   Query from CML API? yes
   How do we track which LabInstanceRequests are assigned to which LabWorker? yes, via a workerRef field on LabInstanceRequest
   Should there be a LabWorkerPool resource to manage multiple workers? yes, ideally LabWorkerPool should be defined per LabTrack (which defines the parent name of a LabInstanceRequest)
1. Configuration & Credentials
   Where should AWS credentials be stored? as env var
   Kubernetes secrets? helm charts
   Environment variables? helm value
   AWS IAM roles? yes - To be confirmed if required
   Where should CML license information be stored? in helm values as env var
   Configuration for:
   AMI ID
   Instance type
   VPC/subnet IDs
   Security group IDs
   Key pair name
1. SPI Interface Definition
   What should the CmlLabWorkers SPI interface look like? For example:

1. Integration Points
   Should LabInstanceRequest have a workerRef field pointing to which LabWorker will host it? yes exactly
   Should there be a scheduler/allocator that assigns LabInstanceRequests to LabWorkers? yes
   How do we handle LabWorker failures? (Reschedule instances to other workers?) depends what and why it failed.

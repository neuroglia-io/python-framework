## Candidate Desktop Controller

Service that enables a Cisco Certifications' Candidate Desktop (incl. VDI or BYOD) to be remotely controlled via a Secured HTTP/REST API.

The app regularly registers to the environment by emitting a "com.cisco.mozart.desktop.registered.v1" cloudevent that includes the IP address of its Docker host.  

*(That is: the app is deployed as a Docker container in a VM (with Docker Desktop, not Kubernetes).*

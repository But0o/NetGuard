# NetGuard

**Network Discovery & Security Monitor**

NetGuard is an educational network monitoring and security project developed in Python.

The main goal of this project is to progressively explore **computer networking, network programming, Linux and cybersecurity** through practical implementation.

Rather than building the entire application at once, NetGuard is being developed incrementally, with each stage introducing new networking concepts, protocols, tools and software engineering practices.

---

## Project Goals

NetGuard aims to progressively provide functionality for:

* Local network discovery
* Host discovery
* Connectivity monitoring
* Latency measurement
* TCP port scanning
* Basic service detection
* DNS information
* Network inventory
* Historical monitoring
* Network security events
* Basic threat detection
* REST API
* Network monitoring dashboard

The project is primarily focused on **learning and experimentation**.

---

## Learning Objectives

This project is being used to develop practical knowledge of:

### Networking

* IPv4 / IPv6
* Subnets
* CIDR
* TCP/IP
* ICMP
* TCP
* UDP
* ARP
* DNS
* Ports
* Routing
* Network interfaces
* Network latency
* Packet loss

### Network Programming

* Python sockets
* TCP connections
* UDP communication
* Network discovery
* Concurrent connections
* Network monitoring

### Cybersecurity

* Network reconnaissance
* Port scanning
* Traffic analysis
* Suspicious activity detection
* Network monitoring
* Security events
* Basic IDS concepts

### Software Development

* Python
* FastAPI
* Testing
* Modular architecture
* Logging
* JSON-based persistence
* Git
* GitHub
* Technical documentation

---

## Development Roadmap

### Phase 1 — Network Discovery

* [x] Detect local network interfaces
* [x] Determine local IP address
* [ ] Determine network and CIDR
* [ ] Discover active hosts

### Phase 2 — Connectivity Monitoring

* [ ] ICMP/Ping monitoring
* [ ] Latency measurement
* [ ] Timeout handling
* [ ] Packet loss calculation
* [ ] Monitoring logs

### Phase 3 — Port Scanning

* [ ] TCP socket scanning
* [ ] Configurable port ranges
* [ ] Connection timeout
* [ ] Concurrent scanning
* [ ] Basic service detection

### Phase 4 — DNS

* [ ] DNS lookup
* [ ] Reverse DNS
* [ ] A records
* [ ] AAAA records
* [ ] CNAME records
* [ ] MX records
* [ ] NS records
* [ ] TXT records

### Phase 5 — Network Inventory

* [ ] Host information
* [ ] Hostnames
* [ ] MAC addresses
* [ ] Open ports
* [ ] Detected services
* [ ] Scan timestamps
* [ ] JSON persistence

### Phase 6 — Monitoring

* [ ] Availability monitoring
* [ ] Latency history
* [ ] Packet loss history
* [ ] Event logging
* [ ] Historical data

### Phase 7 — Network Security

* [ ] Connection monitoring
* [ ] Port scan detection
* [ ] Suspicious activity rules
* [ ] Security events
* [ ] Basic IDS concepts

### Phase 8 — API

* [ ] FastAPI integration
* [ ] REST endpoints
* [ ] Network information endpoints
* [ ] Host endpoints
* [ ] Scan endpoints
* [ ] Monitoring endpoints
* [ ] Security event endpoints

### Phase 9 — Dashboard

* [ ] Network overview
* [ ] Active hosts
* [ ] Port information
* [ ] Latency
* [ ] Monitoring history
* [ ] Security events
* [ ] Alerts

---

## Planned Architecture

The architecture will evolve progressively as the project grows.

The initial implementation will remain intentionally simple.

A possible future structure:

```text
netguard/
│
├── app/
│   ├── core/
│   ├── network/
│   ├── scanner/
│   ├── monitoring/
│   ├── security/
│   ├── api/
│   └── models/
│
├── tests/
├── docs/
├── data/
├── scripts/
│
├── README.md
├── pyproject.toml
└── requirements.txt
```

This structure is intentionally not implemented all at once.

---

## Documentation

The project documentation will contain not only usage instructions but also networking concepts and technical decisions learned throughout development.

Planned documentation:

```text
docs/
├── networking/
├── architecture/
├── security/
├── development/
└── experiments/
```

---

## Git Workflow

Development is organized into small, meaningful commits.

Examples:

```text
feat: add local interface discovery
feat: implement host discovery
feat: add TCP port scanner
fix: handle connection timeout
test: add CIDR validation tests
refactor: separate scanner service
docs: document ICMP monitoring
security: add port scan detection rule
```

The repository history is intentionally part of the project.

It should show how NetGuard evolved from a simple networking experiment into a more complete network monitoring and security application.

---

## Security Notice

NetGuard is an educational project.

Network scanning and security-related functionality should only be used against systems and networks that you own or are explicitly authorized to test.

Do not use the project to scan or interact with networks without authorization.

---

## Status

**Project status:** Early development

The project is currently being developed incrementally as a personal learning and portfolio project.

---

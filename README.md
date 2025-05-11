# Instabug Infrastructure Internship Task

This repository is my submission for the **2025 Infrastructure Internship Position** at **Instabug**.

I'd like to thank the Instabug Infrastructure Team for designing this challenge, it pushed me to dive deep into Kubernetes, sealed-secrets, and Go programming. Before this task, I had:

- ❌ Very limited experience with Kubernetes
- ❌ No experience with sealed-secrets
- ❌ No experience with Go

Despite that, I spent several focused days learning and building, not just writing a documentation-only solution, as I believe in learn by doing. I managed to implement a working proof-of-concept with both **Python scripting** and **source code changes** to the official `kubeseal` CLI. This README documents my process, thought journey, and deliverables.

---

## 🤖 Disclaimer on AI Tools Usage

I value transparency and learning, so I focused on learning and thinking independently throughout this challenge. However, I used some AI tools in the following ways only:

* Study roadmap planning
* Installing Docker/Minikube on Windows
* Markdown formatting help
* Python helper functions
* Fixing errors in Python & Go
* Translating Python to Go

> 📌 This README and all explanations were fully written by me. AI was used only for formatting help.

---

## 📦 Repository Overview

This repository includes:

- **Comprehensive Documentation:** Step-by-step explanation of my approach, design decisions, and technical challenges.
- **Python Script Proof-of-Concept:** A script that automates the process of re-encrypting all SealedSecrets in a Kubernetes cluster.
- **Source Code Modifications:** Changes to the official `kubeseal` CLI (located in `cmd/kubeseal`) to add a new `--reencrypt-all` flag, enabling cluster-wide SealedSecret re-encryption directly from the CLI.

---

## 📚 Table of Contents

- Problem Statement
- Requirements
- Prerequisites
- Installation
- First Attempt
- Second Attempt
- Modifying the Source Code
- Testing
- Security
- Logging
- Handling Large Inputs
- Concerns and Future Work
- References

---

## 📌 Problem Statement

> Implement a mechanism for automating the process of re-encrypting all SealedSecrets in a Kubernetes cluster as an additional feature to the `kubeseal` CLI. Explain the implementation steps, considerations, challenges, and benefits of integrating this functionality.

---

## ✅ Requirements

- Identify all existing SealedSecrets in the cluster.
- Fetch all active public keys of the SealedSecrets controller.
- Decrypt SealedSecrets using the corresponding private keys.
- Re-encrypt secrets using the latest public key.
- Update the SealedSecret objects with re-encrypted data.
- ✅ Bonus: Logging/reporting mechanism.
- ✅ Bonus: Handle large clusters efficiently.
- ✅ Bonus: Ensure key security.
- Deliver a Markdown documentation file.

---

## ⚙️ Prerequisites

- Docker Desktop
- kubectl CLI
- Minikube
- Sealed-Secrets controller installed in cluster
- Go programming language installed

---

## 🧪 Installation

### 1. Install Prerequisites

- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)**  
  Download and install Docker Desktop for your OS.

- **[Minikube](https://minikube.sigs.k8s.io/docs/start/)**  
  Follow the [official guide](https://minikube.sigs.k8s.io/docs/start/) to install Minikube.

- **[kubectl](https://kubernetes.io/docs/tasks/tools/)**  
  Install the Kubernetes CLI if you don't have it already.

- **Go Programming Language**  
  Download from [golang.org](https://go.dev/dl/).

---

### 2. Start a Local Kubernetes Cluster

```bash
minikube start --driver=docker
```

---

### 3. Install the Sealed-Secrets Controller

```bash
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.29.0/controller.yaml
```

Wait for the controller pod to be ready:
```bash
kubectl -n kube-system get pods -A
```
> You should see a pod named sealed-secrets-controller-abc123 (any random number)
---

### 4. Clone and Build the Custom `kubeseal` CLI

```bash
git clone https://github.com/bitnami-labs/sealed-secrets.git
cd sealed-secrets/cmd/kubeseal
go build -o mykubeseal.exe
```

---

### 5. Verify Installation

Check that your custom CLI works:
```bash
.\mykubeseal.exe --help
```

---

We now have a local Kubernetes cluster with Sealed-Secrets and a custom `kubeseal` CLI ready for use.

---

## 🚀 First Attempt

After learning more about kubeseal from tutorials and reading its documentation, I found the required commands to do the main requirements.

### Steps:

1. List all existing SealedSecrets in all namespaces:

   ```bash
   kubectl get sealedsecrets --all-namespaces
   ```

2. Fetch latest public cert which includes the encryption public key:

   ```bash
   kubeseal --fetch-cert
   ```
Note that in the requirements it was asked to "fetch all active public keys", I couldn't find any commands that does that. I thought of using a data structure to manage the created public keys with their creation dates but I think this is not necessary. If we are aiming for re-encryption, the old public keys should be not used, as this might be a security threat.

3. Reseal each secret manually:

   ```bash
   kubeseal --cert cert.pem --format yaml < secret.yaml > sealed.yaml
   kubectl apply -f sealed.yaml
   ```

### ❌ Problems:

This approach from my opinion is not secure. Anyone can easily have a look at the original secret plaintext by printing it to the terminal if they have access. I wanted to find a way to prevent this. Also, this approach may not be suitable if I want to delete the secret.yaml file and only keep sealed-secret.yaml
I had a look at the Sealed-Secrets documentation and found a great flag that can be used to achieve the required, let's move to the second attempt.

---

## 🔐 Second Attempt

I discovered the official `--re-encrypt` flag from Sealed-Secrets documentation, which allows:

* Decrypting a SealedSecret using the controller's private key without exposing it.
* Re-encrypting it using the latest public key.

```bash
kubeseal --re-encrypt --cert cert.pem < sealedsecret.yaml > newsealed.yaml
kubectl apply -f newsealed.yaml
```

✅ This avoids touching the original `secret.yaml`, and is much safer and cleaner. I tested this approach with a Python script before going into `kubeseal` source code.

---

## 🛠 Modifying the Source Code

To go beyond scripting, I added this as a **new top-level flag** inside the actual `kubeseal` CLI source.

### What I did:

* Cloned the repo.
* Navigated to `cmd/kubeseal/main.go`.
* Added a new flag `--reencrypt-all` in `main.go`
* Added `ReEncryptAllSealedSecrets` function
* Built my custom CLI:

  ```bash
  go build -o mykubeseal.exe
  ```

### What `--reencrypt-all` does:

* Fetches all SealedSecrets in all namespaces.
* Fetches the latest cert from the controller.
* Re-encrypts each secret (securely, using stdin/stdout piping in Go).
* Applies the updated SealedSecret to the cluster.

---

## 🧪 Testing

### Manual test workflow:

1. Create a test secret:

   ```bash
   kubectl apply -f buginsta-secret.yaml
   ```

2. Seal the secret:

   ```bash
   kubectl get secret buginsta-task-secret -o yaml | .\mykubeseal.exe --format yaml > buginsta-sealedsecret.yaml
   ```

3. Delete the original secret:

   ```bash
   kubectl delete secret buginsta-task-secret
   ```

4. Apply sealed secret:

   ```bash
   kubectl apply -f buginsta-sealedsecret.yaml
   ```

5. Run the new --reencrypt-all flag:

   ```bash
   .\mykubeseal.exe --reencrypt-all
   ```

6. Verify output changed:

   ```bash
   kubectl get sealedsecret buginsta-task-secret -o yaml > before.yaml
   ./mykubeseal.exe --reencrypt-all
   kubectl get sealedsecret buginsta-task-secret -o yaml > after.yaml
   ```

The encrypted content of `before.yaml` and `after.yaml` should differ, this proves re-encryption is working correctly.
Note that the cert and the plaintext has not changed, but Sealed-Secrets used a unique session key for each encryption to randomize the ciphertext each time we run the command.

7. Confirm controller restores the secret:

   ```bash
   kubectl get secret buginsta-task-secret -o yaml
   ```

---

## 🔑 Security

> The private key is securely stored inside the controller pod and is never exposed to users or external tools. For this proof-of-concept, re-encryption was performed in a privileged environment with access to the private key (inside the controller pod). In any production or shared environment, it is essential to limit access to the private key and avoid exposing it outside the cluster to maintain the confidentiality of all sealed secrets.


---

## 📋 Logging

I made the Python script log each step if it passes or fails. For each run, a separate log file is created, instead of logging everything into one single file. This was inspired from my small experience with the Yocto build tool for Embedded Linux.
   ```log
  2025-05-08 23:34:04,892 [INFO] Fetching current public key from the SealedSecrets controller...
  2025-05-08 23:34:05,071 [INFO] Found 1 SealedSecrets. Starting reseal process...
  2025-05-08 23:34:05,072 [INFO] Processing default/buginsta-task-secret...
  2025-05-08 23:34:07,072 [INFO] Successfully resealed and updated default/buginsta-task-secret
  2025-05-08 23:34:07,073 [INFO] Reseal process completed.
   ```

---

## ⚡ Handling Large Inputs

I am currently studying High Performance Computing, so I thought it might be a good idea to use multithreading to solve this problem. We can distribute the load to a fixed amount of threads or we can configure it dynamically based on the number of SealedSecrets.
I implemented multithreading in the Python script to handle multiple secrets.
  ```python
    with ThreadPoolExecutor(max_workers=5) as executor:
      for secret in secrets:
          executor.submit(reseal_secret, secret, cert_path)
  ```
---

## 🧠 Concerns and Future Work

### Concerns:

* What happens if the controller crashes? There should be a key backup or restore mechanism.
* For CI/CD, CLI may not be the best interface, GitOps may be more robust.

### Future Work:

* [ ] Dockerized version of the tool for testing ease.
* [ ] Add `--dry-run`, `--namespace`, `--filter` flags.
* [ ] Write shell scripts to automate testing and validation.
* [ ] Use go routines to handle large number of secrets

---

## 📚 References

* [Bitnami Sealed Secrets GitHub](https://github.com/bitnami-labs/sealed-secrets)
* [Tech With Nana – Kubernetes Playlists](https://www.youtube.com/@TechWorldwithNana)
* [KodeKloud, DevOps Directive](https://www.youtube.com)
* [LinkedIn Learning: Learning Kubernetes](https://www.linkedin.com/learning)

---

## 💌 Final Thoughts

Thank you again to the Instabug team for creating such a great challenge ❤️

I had a blast building this. I hope you enjoy reviewing it just as much!

— **Abdelrahman**
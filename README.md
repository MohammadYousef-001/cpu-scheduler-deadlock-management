# CPU Scheduler with Deadlock Detection and Recovery

## 📌 Description
This project implements a CPU scheduling system that simulates an operating system scheduler. It combines Priority Scheduling and Round Robin (RR) while handling CPU bursts, I/O operations, resource allocation, and deadlock management.

## 🎯 Objective
To design and implement a process scheduler that efficiently manages multiple processes while detecting and resolving deadlocks.

---

## ⚙️ Features

### 🧠 Scheduling
- Priority Scheduling (lower number = higher priority)
- Round Robin (RR) for processes with the same priority
- Time quantum execution

### 🔄 Process Handling
- CPU bursts execution
- I/O burst simulation
- Dynamic process arrival

### 🔧 Resource Management
- Resource allocation and deallocation
- Waiting queue for processes blocked on resources

### ⚠️ Deadlock Handling
- Resource Allocation Graph (RAG)
- Deadlock detection using DFS cycle detection
- Deadlock recovery by terminating lowest-priority process
- Restarting terminated processes

---

## 📂 Input Format
1 0 1 CPU{R[1] 5 F[1]} IO{3} CPU{2}



### Explanation:
- `1` → Process ID  
- `0` → Arrival time  
- `1` → Priority  
- `CPU{R[1] 5 F[1]}` → Request resource 1, execute for 5 units, then free it  
- `IO{3}` → I/O burst for 3 time units  
- `CPU{2}` → CPU burst for 2 time units  

---

## ▶️ How to Run

```bash
python main.py



Processes are read from a file called `input.txt`.

### Example:

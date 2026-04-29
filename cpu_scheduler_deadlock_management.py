##############################################################################################################################################################
import copy
import re


class Process:
    def __init__(self, pid, arrivaltime, priority, cpu_bursts=None):
        self.pid = pid
        self.arrivaltime = arrivaltime
        self.priority = priority
        self.cpu_bursts = cpu_bursts if cpu_bursts else []
        self.current_burst_index = 0  # Tracks the current burst being executed

    def __repr__(self):
        return (
            f"Process(pid={self.pid}, arrivaltime={self.arrivaltime}, "
            f"priority={self.priority}, cpu_bursts={self.cpu_bursts})"
        )


class Resource:
    def __init__(self, id, is_allocated=0, allocated_by=-1):
        self.id = id
        self.is_allocated = is_allocated
        self.allocated_by = allocated_by

    def __repr__(self):
        return (
            f"Resource(id={self.id}, is_allocated={self.is_allocated}, "
            f"allocated_by={self.allocated_by})"
        )

    def allocate(self, pid):
        print(f"DEBUG: Resource {self.id} allocated to Process {pid}")
        self.is_allocated = 1
        self.allocated_by = pid

    def free(self, pid):
        if self.allocated_by == pid:
            print(f"DEBUG: Resource {self.id} freed by Process {pid}")
            self.is_allocated = 0
            self.allocated_by = -1


class Scheduler:
    def __init__(self, processes, quantum, resources):
        self.original_processes = {p.pid: copy.deepcopy(p) for p in processes}
        self.processes = [copy.deepcopy(process) for process in processes]
        self.quantum = quantum
        self.clock = 0
        self.ready_queue = []
        self.waiting_queue = []  # NEW: Waiting queue for processes waiting on resources
        self.io_in_progress = []
        self.resources = resources
        self.gantt_chart = []
        self.waiting_times = initializewaitingtimes(self.processes)
        self.turnaround_times = {}
        self.terminated_processes = []
    def schedule(self):
        print(" Starting scheduling")
        self.processes.sort(key=lambda p: p.arrivaltime)

        while self.processes or self.ready_queue or self.io_in_progress or self.waiting_queue:
            print(f" Clock: {self.clock}")
            print(f" Ready Queue: {[p.pid for p in self.ready_queue]}")
            print(f" Waiting Queue: {[p.pid for p in self.waiting_queue]}")
            print(f" IO In Progress: {[p[0].pid for p in self.io_in_progress]}")

            self.movearrivedprocessestoreadyqueue()
            self.processiobursts()
            self.checkwaitingqueue()  # NEW: Check waiting queue for resource availability

            if self.ready_queue:
                self.executecpuburst()
            else:
                print(" No processes in ready queue, incrementing clock")
                self.clock += 1

        self.printresults()

    def recoverfromdeadlock(self, graph):
        
        print(" Deadlock detected! Initiating recovery process.")

        # Identify processes involved in the deadlock
        involved_processes = {node[2:] for node in graph if node.startswith("P_")}
        involved_processes = [p for p in self.ready_queue + self.waiting_queue if str(p.pid) in involved_processes]

        # Sort processes by the termination criteria (priority, PID)
        involved_processes.sort(
            key=lambda p: (p.priority, -p.pid)
        )

        # Terminate the selected process
        process_to_terminate = involved_processes[0]
        print(f" Terminating Process {process_to_terminate.pid} (Priority: {process_to_terminate.priority})")

        # Release any allocated resources
        for resource_id, resource in self.resources.items():
            if resource.allocated_by == process_to_terminate.pid:
                resource.free(process_to_terminate.pid)

        # Remove the process from queues and save it for restarting later
        if process_to_terminate in self.ready_queue:
            self.ready_queue.remove(process_to_terminate)
        if process_to_terminate in self.waiting_queue:
            self.waiting_queue.remove(process_to_terminate)

        self.terminated_processes.append(process_to_terminate)

        # Check if deadlock is resolved
        graph = createresourceallocationgraph(self.processes, self.resources, self.waiting_queue)
        if detectdeadlock(graph):
            print(" Deadlock still present after terminating a process. Retrying recovery...")
            self.recoverfromdeadlock(graph)  # Recursively recover if deadlock persists
        else:
            print(" Deadlock resolved.")
            for process in self.waiting_queue[:]:  # Iterate over a copy of the waiting queue
                
                self.ready_queue.append(process)
                self.waiting_queue.remove(process)
                print(f" Process {process.pid} moved from waiting queue to priority queue.")
            print(f" Ready Queue: {[f'Process {p.pid} (Priority: {p.priority}, Current Burst: {p.cpu_bursts[p.current_burst_index] if p.current_burst_index < len(p.cpu_bursts) else "Completed"})' for p in self.ready_queue]}")

            # Sort the ready queue by priority to form the new priority queue
            self.ready_queue.sort(key=lambda p: p.priority)
            print(f" Ready Queue after sorting: {[f'Process {p.pid} (Priority: {p.priority}, Current Burst: {p.cpu_bursts[p.current_burst_index] if p.current_burst_index < len(p.cpu_bursts) else "Completed"})' for p in self.ready_queue]}")

            # Restart terminated processes from their original state
            for terminated_process in self.terminated_processes:
                print(f" Restarting Process {terminated_process.pid} from its original state.")
                original_process = copy.deepcopy(self.original_processes[terminated_process.pid])

                # Add the restarted process to the ready queue
                print(f" Process {original_process.pid} re-entered the ready queue.")
                self.ready_queue.append(original_process)

            # Clear the list of terminated processes
            self.terminated_processes.clear()



    def movearrivedprocessestoreadyqueue(self):
        arriving = [p for p in self.processes if p.arrivaltime <= self.clock]
        for process in arriving:
            print(f" Process {process.pid} moved to ready queue")
            self.ready_queue.append(process)
            self.processes.remove(process)

    def processiobursts(self):
        completed_io = []
        
        for process, end_time in self.io_in_progress:
            if self.clock >= end_time:  # Check if IO burst is completed
                print(f" Process {process.pid} completed IO burst at time {self.clock}")

                # Handle the next burst
                if process.current_burst_index < len(process.cpu_bursts):
                    next_burst = process.cpu_bursts[process.current_burst_index]

                    if next_burst[0] == 1:  # CPU burst
                        self.ready_queue.append(process)  # Send back to the ready queue
                        print(f" Process {process.pid} moved to ready queue after IO burst")

                    elif next_burst[0] == 2:  # Free resource
                        resource_id = next_burst[1]
                        self.resources[resource_id].free(process.pid)
                        print(f" Process {process.pid} freed Resource {resource_id} after IO burst")
                        process.current_burst_index += 1
                        self.handlenextburst(process, [])  # Recursively handle next burst
                else:
                    # If there are no more bursts, the process is complete
                    self.turnaround_times[process.pid] = self.clock - process.arrivaltime
                    print(f" Process {process.pid} completed at time {self.clock}, Turnaround Time: {self.turnaround_times[process.pid]}")

                completed_io.append((process, end_time))

        # Remove completed IO bursts from the in-progress queue
        for entry in completed_io:
            self.io_in_progress.remove(entry)
    def allocateavailableresources(self, process, requested_resources):
        
        allocated_resources = []

        for resource_id in requested_resources:
            # Access the resource from the scheduler's resources dictionary
            resource = self.resources.get(resource_id)
            if resource and (not resource.is_allocated or resource.allocated_by == process.pid):
                # Allocate the resource to the process
                resource.allocate(process.pid)
                allocated_resources.append(resource_id)
            else:
                print(f"Resource {resource_id} is unavailable for Process {process.pid}.")

        if allocated_resources:
            print(f" Process {process.pid} successfully allocated Resources {allocated_resources}.")
        else:
            print(f" No resources allocated to Process {process.pid}.")

        return allocated_resources
    

    def calculateaveragetimes(self):
        
        if not self.waiting_times or not self.turnaround_times:
            print(" No processes have completed yet. Cannot calculate averages.")
            return

        # Calculate averages
        total_processes = len(self.waiting_times)
        average_waiting_time = sum(self.waiting_times.values()) / total_processes
        average_turnaround_time = sum(self.turnaround_times.values()) / total_processes

        # Print results
        print("\n Avergae waiting times\n ")
        print(f"Average Waiting Time: {average_waiting_time:.2f} units")
        print(f"Average Turnaround Time: {average_turnaround_time:.2f} units")
    
    # Updated `executecpuburst` with deadlock detection
    def executecpuburst(self):
        print(f"Executing CPU burst at time {self.clock}")
        highest_priority = min(p.priority for p in self.ready_queue)
        priority_queue = [p for p in self.ready_queue if p.priority == highest_priority]
        self.ready_queue = [p for p in self.ready_queue if p.priority != highest_priority]

        if len(priority_queue) > 1:  # More than one process, apply RR
            print(f" Starting Round Robin for priority {highest_priority}")
            while priority_queue:
                self.movearrivedprocessestoreadyqueue()
                process = priority_queue.pop(0)

                if process.current_burst_index >= len(process.cpu_bursts):
                    continue  # Skip completed processes

                current_burst = process.cpu_bursts[process.current_burst_index]

                if current_burst[0] == 1:  # CPU burst
                    required_resources = current_burst[1]  # List of required resources
                    availableResources = self.allocateavailableresources(process, required_resources)

                    # Check if all required resources are available
                    if all(
                        not self.resources[r].is_allocated or self.resources[r].allocated_by == process.pid
                        for r in required_resources
                    ):
                        # Allocate all required resources
                        for resource_id in required_resources:
                            self.resources[resource_id].allocate(process.pid)
                        print(f" Process {process.pid} allocated Resources {required_resources} at time {self.clock}")

                        # Execute the burst for one quantum or until completion
                        burst_time = min(self.quantum, current_burst[2])
                        remaining_time = self.quantum - burst_time
                        self.executeburst(process, burst_time, priority_queue)

                        if current_burst[2] == 0:  # Burst completed
                            process.current_burst_index += 1

                            # If there is remaining quantum time, execute the next burst if it exists
                            if remaining_time > 0 and process.current_burst_index < len(process.cpu_bursts):
                                next_burst = process.cpu_bursts[process.current_burst_index]
                                if next_burst[0] == 1:  # Next burst is also a CPU burst
                                    required_resources = next_burst[1]  # Resources required for the next burst
                                    availableResources = self.allocateavailableresources(process, required_resources)
                                    print(f" Available Resources: {availableResources}")

                                    # Check if all required resources are available
                                    if all(
                                        not self.resources[r].is_allocated or self.resources[r].allocated_by == process.pid
                                        for r in required_resources
                                    ):
                                        # Allocate resources for the next burst
                                        for resource_id in required_resources:
                                            self.resources[resource_id].allocate(process.pid)
                                        print(f" Process {process.pid} allocated Resources {required_resources} for the next burst at time {self.clock}")

                                        # Execute the next burst using the remaining quantum time
                                        next_burst_time = min(remaining_time, next_burst[2])
                                        print(f" Process {process.pid} continues with next burst using {next_burst_time} units.")
                                        self.executeburst(process, next_burst_time, priority_queue)

                                        # Check if the next burst is completed
                                        if next_burst[2] == 0:
                                            process.current_burst_index += 1
                                            self.handlenextburst(process, priority_queue)
                                        else:  # If the next burst is partially executed
                                            priority_queue.append(process)
                                    else:
                                        # Resources not available; move the process to the waiting queue
                                        print(f" Process {process.pid} moved to waiting queue for Resources {required_resources}")
                                        self.waiting_queue.append(process)
                                        ## call same
                                        graph = createresourceallocationgraph(self.processes, self.resources, self.waiting_queue)
                                        if detectdeadlock(graph) and not priority_queue:
                                            print(f"WARNING: Deadlock detected after Process {process.pid} moved to waiting queue!")
                                            print("\nResource Allocation Graph (RAG):")
                                            for node, edges in graph.items():
                                                print(f"{node} -> {edges}")
                                            self.recoverfromdeadlock(graph)
                                else:  # If the next burst is not a CPU burst
                                    self.handlenextburst(process, priority_queue)
                            else:
                                self.handlenextburst(process, priority_queue)
                        else:  # If burst not finished
                            priority_queue.append(process)  # Add back to the priority queue

                    else:
                        # Resources not available, move to waiting queue
                        print(f" Process {process.pid} moved to waiting queue for Resources {required_resources}")
                        self.waiting_queue.append(process)

                        # Trigger deadlock detection
                        graph = createresourceallocationgraph(self.processes, self.resources, self.waiting_queue)
                        if detectdeadlock(graph) and not priority_queue:
                            print(f"WARNING: Deadlock detected after Process {process.pid} moved to waiting queue!")
                            print("\nResource Allocation Graph (RAG):")
                            for node, edges in graph.items():
                                print(f"{node} -> {edges}")
                            self.recoverfromdeadlock(graph) # Temporarily exit the program until recovery is implemented

                elif current_burst[0] == 0:  # IO burst
                    io_burst_time = current_burst[2]
                    self.io_in_progress.append((process, self.clock + io_burst_time))
                    print(f" Process {process.pid} started IO burst of {io_burst_time} units")
                    process.current_burst_index += 1
                elif current_burst[0] == 2:  # Freeing resources
                    resource_ids = current_burst[1]
                    for resource_id in resource_ids:
                        self.resources[resource_id].free(process.pid)
                    print(f" Process {process.pid} freed Resources {resource_ids} at time {self.clock}")
                    process.current_burst_index += 1
                    self.handlenextburst(process, priority_queue)

                # Check for new arrivals in the ready_queue after executing one quantum
                self.movearrivedprocessestoreadyqueue()
                higher_priority_found = self.checkpriorityqueueduringrr(priority_queue, highest_priority)
                if higher_priority_found:
                    # Preempt all RR processes if a higher-priority process arrives
                    print(" Higher priority process found, preempting RR")
                    self.ready_queue.extend(priority_queue)  # Return RR processes to the ready queue
                    return  # Exit RR to handle the higher-priority process

                
        if len(priority_queue) == 1:  # Only one process, execute tick-by-tick
            process = priority_queue[0]

            if process.current_burst_index >= len(process.cpu_bursts):
                print(f" Process {process.pid} has completed all bursts.")
                return  # Process is done

            current_burst = process.cpu_bursts[process.current_burst_index]

            if current_burst[0] == 1:  # CPU burst
                required_resources = current_burst[1]  # List of required resources

                # Check if all required resources are available
                if all(not self.resources[r].is_allocated for r in required_resources):
                    # Allocate all required resources
                    for resource_id in required_resources:
                        self.resources[resource_id].allocate(process.pid)
                    print(f"Process {process.pid} allocated Resources {required_resources} at time {self.clock}")

                    # Execute the burst tick-by-tick
                    start_time = self.clock  # Record start time for the Gantt chart
                    while current_burst[2] > 0:
                        # Decrement the CPU burst by 1
                        current_burst[2] -= 1
                        print(f" Process {process.pid} executing, remaining burst time: {current_burst[2]}")

                        # Increment clock
                        self.clock += 1

                        # Increment waiting time for all processes in the ready queue
                        for p in self.ready_queue:
                            self.waiting_times[p.pid] += 1

                        # Decrement I/O bursts
                        self.processiobursts()

                        # Check for new arrivals
                        self.movearrivedprocessestoreadyqueue()

                    end_time = self.clock  # Record end time for the Gantt chart
                    self.gantt_chart.append((process.pid, start_time, end_time))
                    print(f" Process {process.pid} completed CPU burst at time {self.clock}")
                    process.current_burst_index += 1

                    # Handle the next burst (e.g., freeing resources)
                    if process.current_burst_index < len(process.cpu_bursts):
                        next_burst = process.cpu_bursts[process.current_burst_index]
                        if next_burst[0] == 2:  # Freeing resources
                            resource_ids = next_burst[1]
                            for resource_id in resource_ids:
                                self.resources[resource_id].free(process.pid)
                            print(f" Process {process.pid} freed Resources {resource_ids} at time {self.clock}")
                            process.current_burst_index += 1  # Move to the next burst
                    self.handlenextburst(process, [])

                else:
                    # Resources not available, move to waiting queue
                    print(f" Process {process.pid} moved to waiting queue for Resources {required_resources}")
                    self.waiting_queue.append(process)

                    # Trigger deadlock detection
                    graph = createresourceallocationgraph(self.processes, self.resources, self.waiting_queue)
                    if detectdeadlock(graph) and not priority_queue:
                        print(f"WARNING: Deadlock detected after Process {process.pid} moved to waiting queue!")
                        print("Program exited due to deadlock.")
                        print("\nResource Allocation Graph (RAG):")
                        for node, edges in graph.items():
                            print(f"{node} -> {edges}")

                        # Print the Gantt chart
                        print("\nGantt Chart:")
                        for entry in self.gantt_chart:
                            print(f"Process {entry[0]}: {entry[1]}-{entry[2]}")

                        self.recoverfromdeadlock(graph)  # Temporarily exit the program until recovery is implemented

            elif current_burst[0] == 0:  # IO burst
                io_burst_time = current_burst[2]
                self.io_in_progress.append((process, self.clock + io_burst_time))
                print(f" Process {process.pid} started IO burst of {io_burst_time} units")
                process.current_burst_index += 1
    


    def checkpriorityqueueduringrr(self, priority_queue, current_priority):
       
        higher_priority_found = False

        # Check for new arrivals in the ready queue
        for process in self.ready_queue[:]:  # Iterate over a copy of the ready queue
            if process.priority < current_priority:  # Higher-priority process
                higher_priority_found = True
            elif process.priority == current_priority:  # Same-priority process
                print(f" Process {process.pid} with priority {process.priority} joined RR priority queue")
                self.ready_queue.remove(process)
                priority_queue.append(process)

        return higher_priority_found
    def checkwaitingqueue(self):
        for process in self.waiting_queue[:]:  # Iterate over a copy of the waiting queue
            required_resources = process.cpu_bursts[process.current_burst_index][1]
            if all(not self.resources[r].is_allocated for r in required_resources):
                # If resources are now free, allocate them and move process to ready queue
                print(f"DEBUG: Process {process.pid} moved from waiting queue to ready queue")
                self.waiting_queue.remove(process)
                self.ready_queue.append(process)


    def executeburst(self, process, burst_time, priority_queue):
      
        start_time = self.clock
        burst = process.cpu_bursts[process.current_burst_index]

        for _ in range(burst_time):
            self.movearrivedprocessestoreadyqueue()
            self.processiobursts()
            self.checkwaitingqueue()  # Check waiting queue during execution

            for p in self.ready_queue + priority_queue:
                if p != process:
                    self.waiting_times[p.pid] += 1

            burst[2] -= 1
            self.clock += 1

            if burst[2] == 0:
                break

        print(f" Process {process.pid} executed from {start_time} to {self.clock}")
        self.gantt_chart.append((process.pid, start_time, self.clock))

        # Check for completion after execution
        if burst[2] == 0 and process.current_burst_index == len(process.cpu_bursts) - 1:
            self.turnaround_times[process.pid] = self.clock - process.arrivaltime
            print(f" Process {process.pid} completed at time {self.clock}, Turnaround Time: {self.turnaround_times[process.pid]}")


    def handlenextburst(self, process, priority_queue):
       
        if process.current_burst_index >= len(process.cpu_bursts):
            # No more bursts, process is complete
            self.turnaround_times[process.pid] = self.clock - process.arrivaltime
            print(f" Process {process.pid} completed at time {self.clock}, Turnaround Time: {self.turnaround_times[process.pid]}")
            return

        next_burst = process.cpu_bursts[process.current_burst_index]

        if next_burst[0] == 1:  # Next is a CPU burst
            priority_queue.append(process)            
            print(f" Process {process.pid} moved to priority  queue after finishing previous burst")
        elif next_burst[0] == 0:  # Next is an IO burst
            io_burst_time = next_burst[2]
            self.io_in_progress.append((process, self.clock + io_burst_time))
            print(f" Process {process.pid} started IO burst of {io_burst_time} units")
            process.current_burst_index += 1
        elif next_burst[0] == 2:  # Next is another freeing burst
            resource_ids = next_burst[1]
            for resource_id in resource_ids:
                self.resources[resource_id].free(process.pid)
            print(f"Process {process.pid} freed Resources {resource_ids} at time {self.clock}")
            process.current_burst_index += 1
            self.handlenextburst(process, priority_queue)  # Recursively handle the next burst

    


    def printresults(self):
        print("\nGantt Chart:")

        # Consolidate Gantt chart intervals for the same process
        consolidated_chart = []
        if self.gantt_chart:
            current_process, start_time, end_time = self.gantt_chart[0]
            for entry in self.gantt_chart[1:]:
                if entry[0] == current_process and entry[1] == end_time:
                    # Extend the current interval if it's the same process
                    end_time = entry[2]
                else:
                    # Append the consolidated interval and start a new one
                    consolidated_chart.append((current_process, start_time, end_time))
                    current_process, start_time, end_time = entry
            # Append the last interval
            consolidated_chart.append((current_process, start_time, end_time))

        # Check for idle time and include it in the Gantt chart
        final_chart = []
        previous_end = 0
        for entry in consolidated_chart:
            process_id, start_time, end_time = entry
            if start_time > previous_end:
                # Add idle time if there is a gap
                final_chart.append(("Idle", previous_end, start_time))
            final_chart.append(entry)
            previous_end = end_time

        # Print the final consolidated Gantt chart
        for entry in final_chart:
            process_id, start_time, end_time = entry
            if process_id == "Idle":
                print(f"Idle: {start_time}-{end_time}")
            else:
                print(f"Process {process_id}: {start_time}-{end_time}")

        print("\nWaiting Times for Each Process:")
        for pid, waiting_time in self.waiting_times.items():
            print(f"Process {pid}: {waiting_time} units")

        print("\nTurnaround Times for Each Process:")
        for pid, turnaround_time in self.turnaround_times.items():
            print(f"Process {pid}: {turnaround_time} units")

    

def initializewaitingtimes(processes):
    return {process.pid: 0 for process in processes}


def readprocessesfromfile(filename):
    processes = []
    resources = {}
    with open(filename, "r") as file:
        lines = file.readlines()
        for line_number, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            try:
                # Split line into process attributes
                parts = re.split(r'\s+', line)
                pid = int(parts[0])
                arrivaltime = int(parts[1])
                priority = int(parts[2])

                # Parse CPU/IO bursts
                cpu_bursts = []
                bursts_section = " ".join(parts[3:])
                tokens = re.findall(r"(CPU\{.*?\}|IO\{.*?\})", bursts_section)

                for token in tokens:
                    if token.startswith("CPU{"):
                        inner_burst = token[4:-1]
                        sub_bursts = re.findall(r"(R\[\d+\]|F\[\d+\]|\d+)", inner_burst)

                        resources_list = []
                        i = 0
                        while i < len(sub_bursts):
                            part = sub_bursts[i]

                            if part.isdigit():
                                burst_time = int(part)
                                cpu_bursts.append([1, resources_list, burst_time])
                                resources_list = []
                            elif "R" in part:
                                resource_id = int(re.search(r"\d+", part).group())
                                resources_list.append(resource_id)
                            elif "F" in part:
                                resource_id = int(re.search(r"\d+", part).group())
                                cpu_bursts.append([2, [resource_id], 0])

                            i += 1

                    elif token.startswith("IO{"):
                        time = int(re.search(r"\d+", token).group())
                        cpu_bursts.append([0, [], time])

                # Add resources
                for burst in cpu_bursts:
                    if burst[0] == 1:
                        for resource_id in burst[1]:
                            if resource_id not in resources:
                                resources[resource_id] = Resource(resource_id)
                    if burst[0] == 2:
                        for resource_id in burst[1]:
                            if resource_id not in resources:
                                resources[resource_id] = Resource(resource_id)

                processes.append(Process(pid, arrivaltime, priority, cpu_bursts))
            except ValueError as e:
                print(f"Error parsing line {line_number}: {e}")
                continue

    return processes, resources

##############################################################################################################################################################
def createresourceallocationgraph(processes, resources, waiting_queue):
    
    graph = {}

    # Initialize graph nodes for all processes and resources
    for process in processes + waiting_queue:
        graph[f"P_{process.pid}"] = []  # Add process node

    for resource_id, resource in resources.items():
        graph[f"R_{resource_id}"] = []  # Add resource node

    # Add edges for resource allocation (R -> P)
    for resource_id, resource in resources.items():
        if resource.is_allocated:  # If the resource is currently allocated
            graph[f"R_{resource_id}"].append(f"P_{resource.allocated_by}")  # R -> P edge

    # Add edges for resource requests (P -> R)
    for process in waiting_queue:
        current_burst = process.cpu_bursts[process.current_burst_index]
        if current_burst[0] == 1:  # If it's a CPU burst requiring resources
            for resource_id in current_burst[1]:  # Iterate over required resources
                graph[f"P_{process.pid}"].append(f"R_{resource_id}")  # P -> R edge

    return graph

def detectdeadlock(graph):
    
    visited = set()  # Keeps track of visited nodes
    recursion_stack = set()  # Keeps track of nodes in the current recursion stack (to detect cycles)

    def dfs(node):
        
        # If the node is already in the recursion stack, a cycle is detected
        if node in recursion_stack:
            return True

        # If the node has already been visited and no cycle was detected, skip it
        if node in visited:
            return False

        # Mark the node as visited and add it to the recursion stack
        visited.add(node)
        recursion_stack.add(node)

        # Visit all adjacent nodes
        for neighbor in graph.get(node, []):
            if dfs(neighbor):  # Recursive call
                return True

        # Remove the node from the recursion stack before returning
        recursion_stack.remove(node)
        return False

    # Perform DFS for every node in the graph
    for node in graph:
        if node not in visited:  # Start a new DFS only if the node has not been visited
            if dfs(node):
                return True  # Deadlock detected

    return False  # No deadlock detected


   


def main():
    filename = "input.txt"
    processes, resources = readprocessesfromfile(filename)

    print("\nParsed Processes:")
    for process in processes:
        print(process)

    print("\nParsed Resources:")
    for resource in resources.values():
        print(resource)

    quantum = 10
    scheduler = Scheduler(processes, quantum, resources)
    scheduler.schedule()
    scheduler.calculateaveragetimes()


if __name__ == "__main__":
    main()
import subprocess
import sys
import os
import time

last_request_id = 0

def process(request_id):
    try:
        arguments = open("Requests/request_"+str(request_id)+".txt", "r")
        state = None
        for line in arguments:
            if state is None:
                state = str(line)[:-1]
                state = '_'.join(state.split(' '))
                print(state)
            else:
                bounds = str(line)
        arguments.close()
        command = 'bash -c'
        command = command.split(" ")
        actual_commands = 'ssh -tt squidsurvey@yeeha.cs.umass.edu ssh -tt compute-0-13 /nfs/avid/users2/matteo/sudocu/run_paql_for_state.sh paquid 10 ' + state + ' ' + bounds
        command.append(actual_commands)   
        print(actual_commands)     
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        print(stderr)
        print("Successfully processed request ID", request_id)
        f = open("Requests/response_"+str(request_id)+".txt", "w")
        f.write(stdout.decode("utf-8"))
        f.close()
        os.chmod("Requests/response_"+str(request_id)+".txt", 0o777)
    except:
        f = open("Requests/response_"+str(request_id)+".txt", "w")
        print("Failed to processed request ID" + str(request_id) + '\n')
        f.write("Error")
        f.close()
        os.chmod("Requests/response_"+str(request_id)+".txt", 0o777)

while True:
    time.sleep(2)

    for request in os.listdir("Requests"):
        if request.startswith("request_"):
            request_id = int(request.split('_')[1].split('.')[0])
            if request_id > last_request_id:
                process(request_id)
                last_request_id = request_id
                #os.remove("Requests/" + request)



        
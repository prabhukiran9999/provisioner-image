import subprocess
import os
import json
from subprocess import call
import time
import git
from git import Repo

# Token to use GH CLI and clone the repo
token = os.getenv("token")

#Clone the Github repo
org_name= "prabhukiran9999"
repo_name = "pr-script"
repo_url = f'https://{token}@github.com/{org_name}/{repo_name}.git'

repo_dir = os.path.join(os.getcwd(), repo_name)
os.makedirs(repo_dir, exist_ok=True)

# Clone the repository
git.Repo.clone_from(repo_url, repo_dir, recursive=True)
os.chdir(repo_name)
pwd = os.getcwd()
print (pwd)
repo_path = "./"
repo = Repo(repo_path)

#Get GH Cli version
gh_version = call(["gh", "--version"])


# Execute the `gh auth login` command and provide your personal access token as input
subprocess.run(["gh", "auth", "login", "--with-token"], input=f"{token}\n", text=True)

# Get project data from the json env variable
json_env_var = os.environ.get('json_var')
project_data = json.loads(json_env_var)if json_env_var else {}
project_name = project_data["project_set_info"]["project_name"]
admin_email = project_data["project_set_info"]["admin_email"]
admin_name = project_data["project_set_info"]["admin_name"]
billing_group = project_data["project_set_info"]["billing_group"] 
# Look for a specific key in the JSON object
key="licence_Plate"
LicencePlate = project_data["project_set_info"].get(key)
# Execute project-set creation script
if LicencePlate:
    try :
        os.chdir('./bin')
        pwd = os.getcwd()
        print(pwd)
        subprocess.call(["./project_set_admin.sh", "-lp", f"{LicencePlate}", "-pn", f"{project_name}", "-ae", f"{admin_email}", "-an", f"{admin_name}", "-bg", f"{billing_group}", "-e", "tools", "-e", "dev", "-e", "test", "-e", "prod", "-l", "accounts"])
    except subprocess.CalledProcessError as e:
        print(e)
else:   
    try :
        os.chdir('./bin')
        pwd = os.getcwd()
        print(pwd)
        subprocess.call(['./project_set_admin.sh',"-pn", f"{project_name}", "-ae", f"{admin_email}", "-an", f"{admin_name}", "-bg", f"{billing_group}", "-e", "tools", "-e", "dev", "-e", "test", "-e", "prod", "-l", "accounts"])
    except subprocess.CalledProcessError as e:
        print(e)
os.chdir('../')
# Get the project-set name created
project_Set_info = subprocess.Popen(["git", "ls-files", "--others", "--directory", "--exclude-standard"],stdout=subprocess.PIPE).communicate()[0].decode("utf-8").rstrip()
checkout_branch_name = project_Set_info.strip("/").replace("projects/", "")
print(checkout_branch_name)


#Create a new branch with the name of the project set created
checkout_branch = repo.git.checkout('-b', checkout_branch_name)
# Commit message for Push
COMMIT_MESSAGE = f'Creating accounts for new project set-{checkout_branch_name}'
def git_push():
    branch = checkout_branch_name
    repo = Repo('.')
    repo.git.add(all=True)
    repo.index.commit(COMMIT_MESSAGE)
    remote = repo.remote(name="origin")
    origin = repo.remote(name='origin')
    origin.push(checkout_branch_name)
    
git_push()
time.sleep(5)


## Create Pull reequest and sleep for 5 min
create_pr = subprocess.Popen(["gh", "pr", "create", f"-t Creating accounts for a new project set-{checkout_branch_name}", f"-b creating accounts for a new project set-({checkout_branch_name}) using provisonor script", "-rwrnu"],stdout=subprocess.PIPE).communicate()[0] 
pr_url = create_pr.decode("utf-8").rstrip() 
print (f'Pull_request for new project-set({checkout_branch_name}) accounts created successfully')
#Sleep for 5 sec after pull request is created so the actions will register
time.sleep(5) #Sleep for 5 secs
print(pr_url)

# Check for pull request actions to complete
check_pr = json.loads(subprocess.Popen(["gh", "pr", "view", pr_url, "--json", "statusCheckRollup"],stdout=subprocess.PIPE).communicate()[0].decode("utf-8").rstrip())
print(check_pr)
workflow_id = str(json.loads(subprocess.Popen(["gh", "run", "list", "-b", checkout_branch_name, "-L", "1", "--json", "databaseId"],stdout=subprocess.PIPE).communicate()[0])[0]['databaseId'])
step = "account-creation"

# Function to get the pull request workflow status and merge the PR once the workflow status are successful
def pr_workflow_status(workflow_id,pr_url):
    workflow_status = ""
    while workflow_status != "completed":
        time.sleep(5)
        workflow_status = json.loads(subprocess.Popen(["gh", "run", "view", workflow_id, "--json", "status"],stdout=subprocess.PIPE).communicate()[0])['status']
        workflow_conclusion = json.loads(subprocess.Popen(["gh", "run", "view", workflow_id, "--json", "conclusion"],stdout=subprocess.PIPE).communicate()[0])['conclusion']
        if workflow_status =='queued':
            print(f'pull request workflow status for {step} is {workflow_status}')
            continue
        elif workflow_status == "in_progress":
            print(f'pull request workflow status for {step} is {workflow_status}')
            continue
        elif workflow_status == "completed" and workflow_conclusion == "success":
            print(f'pull request workflow status for {step} is {workflow_status} and is {workflow_conclusion}')
            # Merge pull request when workflow is successful
            merge_pr = subprocess.call(["gh", "pr", "merge", pr_url, "--admin", "-m"])
            if merge_pr == 0:
                print(f"Pull request,{pr_url} merged successfully")
                time.sleep(5)
                return workflow_conclusion
            else:
                print(f"problem merging a PR,{pr_url}")
                break
        elif workflow_status =="completed" and workflow_conclusion == "failure":
            print(f"pull request  workflow for {step} failed")
            return workflow_conclusion
            break

####To do add some delay for the runner to stop and start
# Function to get the Push workflow status
def push_workflow_status(push_workflow_id):
    push_workflow_status = ""
    while push_workflow_status != "completed":
        time.sleep(5)
        push_workflow_status = json.loads(subprocess.Popen(["gh", "run", "view", push_workflow_id, "--json", "status"],stdout=subprocess.PIPE).communicate()[0])['status']
        push_workflow_conclusion = json.loads(subprocess.Popen(["gh", "run", "view", push_workflow_id, "--json", "conclusion"],stdout=subprocess.PIPE).communicate()[0])['conclusion']
        if push_workflow_status =='queued':
            print(f'push workflow status for {step} is {push_workflow_status}')
            continue
        elif push_workflow_status == "in_progress":
            print(f'push workflow status for {step} is {push_workflow_status}')
            continue
        elif push_workflow_status == "completed" and push_workflow_conclusion == "success":
            print(f'push workflow status for {step} is {push_workflow_status} and is {push_workflow_conclusion}')
            return push_workflow_conclusion
        elif push_workflow_status == "completed" and push_workflow_conclusion == "failure":
            print(f"Push workflow for {step} failed")
            return push_workflow_conclusion


pr_workflow_status(workflow_id,pr_url)
time.sleep(5)
push_workflow_id = str(json.loads(subprocess.Popen(["gh", "run", "list", "-b", "main", "-L", "1", "--json", "databaseId"],stdout=subprocess.PIPE).communicate()[0])[0]['databaseId'])
push_status = push_workflow_status(push_workflow_id)
print(push_status)

# Create layers if push workflow status are succesfull
if push_status == "success":
    try :
        os.chdir('./bin')
        layer_creation = subprocess.call(['./project_set_admin.sh',"-lp", f"{checkout_branch_name}", "-l", "alb", "-l", "automation", "-l", "dns", "-l", "sso", "-l", "tfc-aws-automation", "-l", "github-oidc"])
        if layer_creation == 0:
            print("layers created seccussfully") 
        else:
            print(f"problem creating pull request for layers")
    except subprocess.CalledProcessError as e:
        print(e)
else:
    print("Push workflow for accounts failed")

os.chdir('../')
COMMIT_MESSAGE = f'Creating other layers for the project set-{checkout_branch_name}'
git_push()
step = "layer-creation"
layer_pr = subprocess.Popen(["gh", "pr", "create", f"-t Adding Layers to the project set-{checkout_branch_name}", f"-b Adding layers to the new project set-{checkout_branch_name} using provisonor script", "-rwrnu"],stdout=subprocess.PIPE).communicate()[0] 
pr_url = layer_pr.decode("utf-8").rstrip() 
print ('Pull_request for layers created successfully')


#Sleep for 5 sec after pull request is created so the actions will register
time.sleep(5) #Sleep for 5 secs
print(pr_url)
workflow_id = str(json.loads(subprocess.Popen(["gh", "run", "list", "-b", checkout_branch_name, "-L", "1", "--json", "databaseId"],stdout=subprocess.PIPE).communicate()[0])[0]['databaseId'])
pr_workflow_status(workflow_id,pr_url)
time.sleep(5)
push_workflow_id = str(json.loads(subprocess.Popen(["gh", "run", "list", "-b", "main", "-L", "1", "--json", "databaseId"],stdout=subprocess.PIPE).communicate()[0])[0]['databaseId'])
push_status = push_workflow_status(push_workflow_id)
print(push_status)


#Checkout to main and  Delete the branch locally
subprocess.run(f"git checkout main", shell=True)
subprocess.run(f"git branch -D {checkout_branch_name}", shell=True)


# Delete the branch remotely
subprocess.run(f"git push origin --delete {checkout_branch_name}", shell=True)
import subprocess
import logging
import os
import json
import glob
import time
from git import Repo

logging.basicConfig(level=logging.NOTSET)

token = os.getenv("token")
org_name = "bcgov-c"
repo_name = "aws-ecf-forge-workspaces-settings-stack"


def update_submodule_urls(repo, token):
    with open(".gitmodules", "r") as f:
        gitmodules = f.read()

    updated_gitmodules = gitmodules
    for line in gitmodules.split("\n"):
        if "url =" in line and "https://" in line:
            updated_url = line.replace("https://", f"https://{token}@")
            updated_gitmodules = updated_gitmodules.replace(line, updated_url)

    with open(".gitmodules", "w") as f:
        f.write(updated_gitmodules)

    repo.git.submodule("sync")

def clone_and_authenticate(token, org, repo_name):
    repo_url = f'https://{token}@github.com/{org}/{repo_name}.git'
    repo_dir = os.path.join(os.getcwd(), repo_name)
    os.makedirs(repo_dir, exist_ok=True)

    try:
        repo = Repo.clone_from(repo_url, repo_dir)
        subprocess.run(["gh", "auth", "login", "--with-token"], input=f"{token}\n", text=True)
        print(f"GH CLI version: {subprocess.check_output(['gh', '--version']).decode('utf-8')}")
        os.chdir(repo.working_tree_dir)

        # Update submodule URLs with token in .gitmodules and .git/config
        update_submodule_urls(repo, token)

        # Initialize and update the submodules
        repo.git.submodule('update', '--init', '--recursive')

        return repo
    except Exception as e:
        logging.error(f"Error: {e}")
        return None

def git_push(repo, commit_msg, branch_name):
    try:
        # Get a list of all files in the repository
        untracked_files = repo.untracked_files
        modified_files = [item.a_path for item in repo.index.diff(None)]
        all_files = untracked_files + modified_files

        # Filter out the .gitmodules file
        files_to_add = [file for file in all_files if file != ".gitmodules"]

        # Add each file in the filtered list individually
        for file in files_to_add:
            repo.git.add(file)

        repo.index.commit(commit_msg)
        repo.remote(name='origin').push(branch_name)
    except Exception as e:
        print(f"Error: {e}")

def create_pull_request(title, body, reviewers="wrnu"):
    try:
        pr_url = subprocess.check_output(
            [
                "gh",
                "pr",
                "create",
                f"--title={title}",
                f"--body={body}"
                # f"--reviewer={reviewers}"
            ],
            text=True,
        ).strip()

        logging.info(f"Pull_request with title '{title}' created successfully")
        time.sleep(30) #to wait for actions to trigger
        logging.info(pr_url)
        return pr_url
    except subprocess.CalledProcessError as e:
        logging.error(f"Error creating Pull Request: {e}")
        return None

def close_pull_request(pr_status: str, pr_url: str):
    if pr_status == "success":
        close_pr = subprocess.run(["gh", "pr", "close", pr_url], capture_output=True, text=True)
        
        if close_pr.returncode == 0:
            logging.info(f"Pull request {pr_url} closed successfully")
            time.sleep(30) #to wait for actions to trigger
        else:
            logging.error(f"Problem closing PR {pr_url}: {close_pr.stderr.strip()}")

def get_workflow_id(branch_name):
    return str(json.loads(subprocess.check_output(["gh", "run", "list", "-b", branch_name, "-L", "1",
                                                   "--json", "databaseId"]))[0]['databaseId'])

def get_workflow_status(workflow_id):
    try:
        cmd = f"gh run view {workflow_id} --json status,conclusion"

        while True:
            output = subprocess.check_output(cmd, shell=True).decode("utf-8")
            data = json.loads(output)
            status, conclusion = data.get("status"), data.get("conclusion")
            
            print(f"Status: {status}, Conclusion: {conclusion}")

            if status == "completed":
                print( "success" if conclusion == "success" else f"failure: {conclusion}")
                return conclusion
            else:
                print(f"Workflow still {status}, waiting...")
                time.sleep(10)
    except subprocess.CalledProcessError as e:
        return f"An error occurred while fetching the workflow status: {e}"
    
def get_project_data():
    json_env_var = os.environ.get('NATS_MSG')
    return json.loads(json_env_var) if json_env_var else {}

def execute_project_set_admin_script(args, repo_path):
    script_path = os.path.join(repo_path, "source", "bin")
    os.chdir(script_path)
    try:
        subprocess.call(["python3","project_set_admin.py"] + args)
        os.chdir(f"{repo_path}")
    except subprocess.CalledProcessError as e:
        logging.error(e)

# def get_project_set_name(repo_path):
#     os.chdir(repo_path)
#     directories = glob.glob("projects/*/")
#     return os.path.relpath(directories[0], "projects").rstrip("/") if directories else None

def handle_project(repo, LicencePlate, is_update=False):
    action = "Updating" if is_update else "Creating"
    commit_msg = f'{action} project set({LicencePlate})'
    git_push(repo, commit_msg, LicencePlate)
    pr_url = create_pull_request(f"{action} project set-{LicencePlate}",
                                  f"{action} project set-({LicencePlate}) using provisonor script")
    workflow_id = get_workflow_id(LicencePlate)
    pr_status = get_workflow_status(workflow_id)
    if pr_status == "success":
        close_pull_request(pr_status, pr_url)
        workflow_id = get_workflow_id("main")
        push_status = get_workflow_status(workflow_id)
        logging.info(push_status)
    else:
        print(f"pull request workflow at {pr_url} is {pr_status}")

def main():
    project_data = get_project_data()
    project_set_info = project_data.get("project_set_info", {})
    project_name = project_set_info.get("project_name")
    admin_email = project_set_info.get("admin_email")
    admin_name = project_set_info.get("admin_name")
    billing_group = project_set_info.get("billing_group")
    LicencePlate = project_set_info.get('licence_plate')

    repo = clone_and_authenticate(token, org_name, repo_name)
    repo_path = repo.working_tree_dir
    print(repo_path)
#     target_directory_path = os.path.join(repo_path, "projects", LicencePlate) if LicencePlate else None

#     if target_directory_path and os.path.isdir(target_directory_path):
#         print(f"The directory {LicencePlate} exists in the projects folder.")
#         repo.git.checkout('-b', LicencePlate)
#         args = [
#             "-lp", LicencePlate, "-pn", project_name, "-ae", admin_email,
#             "-an", admin_name, "-bg", billing_group
#         ]
#         execute_project_set_admin_script(args, repo_path)
#         handle_project(repo, LicencePlate, is_update=True)
#     else:
#         print(f"The directory {LicencePlate} does not exist in the projects folder.")
#         args = [
#             "-pn", project_name, "-ae", admin_email, "-an", admin_name,
#             "-bg", billing_group, "-e", "tools", "-e", "dev", "-e", "test",
#             "-e", "prod", "-l", "accounts"
#         ]
#         if LicencePlate:
#             args.insert(0, "-lp")
#             args.insert(1, LicencePlate)
#             execute_project_set_admin_script(args, repo_path)
#         else:
#             print("No licence plate provided. Running the project set admin script to create a random Licence Plate")
#             execute_project_set_admin_script(args, repo_path)
#             projects_directory = os.path.join(repo.working_tree_dir, "projects")
#             LicencePlate = os.path.basename(max(glob.glob(os.path.join(projects_directory, "*/")), key=os.path.getctime).rstrip('/'))
#         print(f"Creating a new project set-{LicencePlate} with accounts layer")
#         repo.git.checkout('-b', LicencePlate)
#         handle_project(repo, LicencePlate, is_update=False)
#         print(f"Accounts for project-set {LicencePlate} created. Creating rest of the layers")
#         args = [
#         "-lp", f"{LicencePlate}", "-l", "alb", "-l", "automation", "-l", "dns", "-l", "sso", "-l", "tfc-aws-automation", "-l", "github-oidc"
#         ]
#         execute_project_set_admin_script(args, repo_path)
#         handle_project(repo, LicencePlate, is_update=False)

if __name__ == "__main__":
    main()

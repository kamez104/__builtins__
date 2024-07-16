import time

import Millennium
from datetime import datetime
import pygit2, os, json, shutil
from core.themes import find_all_themes
from core.cfg import cfg
import requests
import arrow

class Updater:

    def get_update_list(self):
        return json.dumps({
            "updates": self.update_list, 
            "notifications": cfg.get_cfg("Themes", "theme_update_notifications")
        })
    
    def set_update_notifs_status(self, status: bool):

        cfg.cfg("Themes", "theme_update_notifications", status)
        return True

    def query_themes(self):
        themes = json.loads(find_all_themes())
        needs_copy = False
        update_queue = []

        for theme in themes:

            path = os.path.join(Millennium.steam_path(), "steamui", "skins", theme["native"])
            # Initialize the repository
            try: 
                repo = pygit2.Repository(path)
                # print(f"successfully opened {theme}")
                self.update_query.append((theme, repo))

            except pygit2.GitError as e:
                if "github" in theme["data"]:
                    needs_copy = True
                    update_queue.append((theme, path))


            except Exception as e:
                # Code to handle the exception
                print(f"An exception occurred: {e}")
                
        if needs_copy:
            source_dir = os.path.join(Millennium.steam_path(), "steamui", "skins")

            # Get the current date and time
            current_date = datetime.now()

            # Convert the date to a string using the strftime() method
            date_string = current_date.strftime('%Y-%m-%d@%H-%M-%S')
            destination_dir = os.path.join(Millennium.steam_path(), "steamui", f"skins-backup-{date_string}")

            if os.path.exists(destination_dir):
                shutil.rmtree(destination_dir)
            # Copy the directory and its contents
            shutil.copytree(source_dir, destination_dir)

        for theme, path in update_queue:

            print(f"upgrading theme to GIT @ {path}")

            if "github" in theme["data"]:
                self.pull_head(path, theme["data"]["github"])

        

    def construct_post_body(self):

        post_body = []

        for theme, repo in self.update_query:

            if "github" in theme.get("data", {}):

                github_data = theme["data"]["github"]
                owner = github_data.get("owner")
                repo = github_data.get("repo_name")
        
                # Skip iteration if either owner or repo is null
                if owner is None or repo is None:
                    continue
        
                post_body.append({'owner': owner, 'repo': repo})

        return post_body
    
    def pull_head(self, path: str, data: any) -> None:

        print(data)

        try:
            shutil.rmtree(path)
            repo_url = f'https://github.com/{data["owner"]}/{data["repo_name"]}.git'
            # Clone the repository
            pygit2.clone_repository(repo_url, path)

        except Exception as e:
            # Code to handle the exception
            print(f"An exception occurred: {e}")

    def update_theme(self, native: str) -> bool:

        print(f"updating theme {native}")
        try: 
            repo = pygit2.Repository(os.path.join(Millennium.steam_path(), "steamui", "skins", native))

            # Fetch the latest changes from the remote
            remote_name = 'origin'
            remote = repo.remotes[remote_name]
            remote.fetch()

            # Get the latest commit from the remote
            latest_commit = repo.revparse_single('origin/HEAD').id 
            print(f"updating {native} to {latest_commit}")

            # Reset the local branch to the remote commit (force update)
            repo.reset(latest_commit, pygit2.GIT_RESET_HARD)

        except pygit2.GitError as e:
            print(e)
            return False
        
        except Exception as e:
            # Code to handle the exception
            print(f"An exception occurred: {e}")
        
        self.re_initialize()
        return True

    def needs_update(self, remote_commit: str, theme: str, repo: pygit2.Repository):

        # Get the default branch name
        # default_branch = repo.active_branch.name

        local_commit = repo[repo.head.target].id
        # print(f"local_commit: {local_commit}, remote_commit: {remote_commit}")

        # Get the local and remote commit hashes for the default branch
        # local_commit = getattr(repo.heads[default_branch], "commit", None)
        needs_update = str(local_commit) != str(remote_commit)

        # # Compare the local and remote commit hashes
        return needs_update
    

    def check_theme(self, theme, repo_name, repo):

        remote = next((item for item in self.remote_json if item.get("name") == repo_name), None)

        if remote is None:
            print(f"no remote found for {repo_name}")
            return

        update_needed = self.needs_update(remote['commit'], theme, repo)

        commit_message = remote['message']
        commit_date = arrow.get(remote['date']).humanize()
        commit_url = remote['url']

        name = theme["data"]["name"] if "name" in theme["data"] else theme["native"]

        if update_needed:
            self.update_list.append({
                'message': commit_message, 'date': commit_date, 'commit': commit_url,
                'native': theme["native"], 'name': name
            })

    def re_initialize(self):
        return self.__init__()

    def __init__(self):

        self.update_list  = []
        self.update_query = []

        self.query_themes()

        start_time = time.time()
        post_body = self.construct_post_body()

        headers = {
            "Content-Type": "application/json"
        }
        # Make the POST request
        response = requests.post("https://steambrew.app/api/v2/checkupdates", data=json.dumps(post_body), headers=headers)

        if response.status_code != 200:
            print("an error occured checking for updates...")
            return 

        remote_json = response.json()
        success = False if "success" in remote_json and not remote_json["success"] else True

        if not success: 
            return 

        self.remote_json = remote_json

        for theme, repo in self.update_query:

            if "data" not in theme:
                continue

            if "github" not in theme["data"]:
                continue

            github_data = theme.get("data", {}).get("github")
            repo_name = github_data.get("repo_name") if github_data else None

            if repo_name:
                self.check_theme(theme, repo_name, repo)       

        if len(self.update_list) > 0:
            print(f"found updates for {[theme['native'] for theme in self.update_list]} in {round((time.time() - start_time) * 1000, 4)} ms")
import logging
from flask import Flask, render_template, request, redirect, url_for
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
from pymongo import MongoClient
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KubernetesClient:
    def __init__(self):
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config.")
        except ConfigException:
            try:
                config.load_kube_config()
                logger.info("Loaded kube config from file.")
            except ConfigException as e:
                logger.error(f"Failed to load Kubernetes config: {e}")
                raise

        self.v1 = client.CoreV1Api()

    def get_pods(self):
        try:
            pod_list = self.v1.list_pod_for_all_namespaces(watch=False)
            pods = [
                {
                    'name': pod.metadata.name,
                    'namespace': pod.metadata.namespace,
                    'status': pod.status.phase,
                    'node_name': pod.spec.node_name
                }
                for pod in pod_list.items
            ]
            logger.info("Retrieved pod information from Kubernetes.")
            return pods
        except client.ApiException as e:
            logger.error(f"Kubernetes API error: {e}")
            return []
        except Exception as e:
            logger.exception("An unexpected error occurred while getting pods.")
            return []

class MongoDBClient:
    def __init__(self):
        self.mongo_client = None
        mongodb_host = os.getenv('MONGODB_HOST')
        mongodb_port = int(os.getenv('MONGODB_PORT', 27017))
        mongodb_username = os.getenv('MONGODB_USERNAME')
        mongodb_password = os.getenv('MONGODB_PASSWORD')

        if not mongodb_host:
            logger.error("MongoDB host is not set in environment variables.")
            return

        try:
            self.mongo_client = MongoClient(
                host=mongodb_host,
                port=mongodb_port,
                username=mongodb_username,
                password=mongodb_password,
                authMechanism="SCRAM-SHA-256",
                authSource="homelabflaskdb"
            )
            self.db = self.mongo_client["homelabflaskdb"]
            self.user_collection = self.db["user_data"]
            logger.info("Connected to MongoDB successfully!")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.mongo_client = None

    def save_user_data(self, data):
        if self.mongo_client:
            try:
                self.user_collection.insert_one(data)
                logger.info("Data saved to MongoDB.")
                return True
            except Exception as e:
                logger.exception("Failed to save data to MongoDB.")
                return False
        else:
            logger.warning("MongoDB connection not established, data not saved.")
            return False

class IndexPage:
    def __init__(self, kubernetes_client):
        self.kubernetes_client = kubernetes_client

    def get_pods_data(self):
        return self.kubernetes_client.get_pods()

    def render(self):
        pods = self.get_pods_data()
        node_name = os.getenv('NODE_NAME', 'Unknown')
        return render_template('index.html', pods=pods, node_name=node_name)

class SubmitPage:
    def __init__(self, mongodb_client):
        self.mongodb_client = mongodb_client

    def process_form(self, request):
        node_name = os.getenv('NODE_NAME', 'Unknown')
        if request.method == 'POST':
            try:
                user_data = request.form
                data = {
                    'name': user_data.get('name'),
                    'email': user_data.get('email'),
                    'message': user_data.get('message'),
                    'node_name': node_name,
                    'ip': request.remote_addr,
                    'user_agent': request.user_agent.string,
                    'referer': request.referrer,
                    'accept_languages': request.accept_languages.to_header(),
                    'cookies': request.cookies,
                    'headers': dict(request.headers),
                    'method': request.method,
                    'path': request.path,
                    'query_string': request.query_string.decode(),
                    'url': request.url,
                    'base_url': request.base_url,
                    'scheme': request.scheme,
                    'host': request.host
                }

                if self.mongodb_client.save_user_data(data):
                    return redirect(url_for('index'))
                else:
                    return render_template('submit.html', node_name=node_name, error="Failed to save data")
            except Exception as e:
                logger.exception("An error occurred during form processing.")
                return render_template('submit.html', node_name=node_name, error="An unexpected error occurred.")

        return render_template('submit.html', node_name=node_name)


class ExperiencePage:
    def __init__(self, mongodb_client):
        self.mongodb_client = mongodb_client

    def get_experiences(self):
        experience_data = list(self.mongodb_client.db["experiences"].find({}))
        return experience_data

    def render(self):
        experience_data = self.get_experiences()
        return render_template('experience.html', experience=experience_data)
class AboutPage:
    def render(self):
        return render_template('about.html')

class SkillsPage:
    def __init__(self, mongodb_client):
        self.mongodb_client = mongodb_client

    def get_skills(self):
        skills = list(self.mongodb_client.db["skills"].find({}))
        return skills

    def render(self):
        skills = self.get_skills()
        return render_template('skills.html', skills=skills)
    

class ProjectsPage:
    def __init__(self, mongodb_client):
        self.mongodb_client = mongodb_client

    def get_projects(self):
        projects = list(self.mongodb_client.db["project"].find({}))
        return projects

    def render(self):
        projects = self.get_projects()
        return render_template('projects.html', projects=projects)

# class ProjectsPage:
#     def render(self):
#         return render_template('projects.html')

class InfrastructurePage:
    def render(self):
        return render_template('infrastructure.html')

class ContactPage:
    def render(self):
        return render_template('contact.html')

app = Flask(__name__)
kubernetes_client = KubernetesClient()
mongodb_client = MongoDBClient()

@app.route('/')
def index():
    page = IndexPage(kubernetes_client)
    return page.render()

@app.route('/about')
def about():
    page = AboutPage()
    return page.render()

@app.route('/experience')
def experience():
    page = ExperiencePage(mongodb_client)
    return page.render()

@app.route('/skills')
def skills():
    page = SkillsPage(mongodb_client)
    return page.render()

@app.route('/projects')
def projects():
    page = ProjectsPage(mongodb_client)
    return page.render()

# @app.route('/projects')
# def projects():
#     page = ProjectsPage()
#     return page.render()

@app.route('/infrastructure')
def infrastructure():
    page = InfrastructurePage()
    return page.render()

@app.route('/contact')
def contact():
    page = ContactPage()
    return page.render()

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    page = SubmitPage(mongodb_client)
    return page.process_form(request)

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
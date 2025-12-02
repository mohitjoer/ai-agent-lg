from langchain.chat_models import init_chat_model
from src.models.schemas import State
from src.config.settings import settings
from github import Github
import re

llm = init_chat_model(settings.LLM_MODEL)

def extract_github_url(text: str) -> tuple:
    """Extract GitHub URL and parse owner/repo from text"""
    github_pattern = r'https?://github\.com/([\w-]+)/([\w-]+)'
    match = re.search(github_pattern, text)
    if match:
        owner = match.group(1)
        repo = match.group(2)
        return match.group(0), owner, repo
    return None, None, None

def fetch_repo_data(owner: str, repo: str):
    """Fetch repository data using GitHub API"""
    try:
        g = Github(settings.GITHUB_TOKEN)
        repository = g.get_repo(f"{owner}/{repo}")
        
        # Fetch repository information
        repo_data = {
            "name": repository.name,
            "full_name": repository.full_name,
            "description": repository.description,
            "stars": repository.stargazers_count,
            "forks": repository.forks_count,
            "open_issues": repository.open_issues_count,
            "language": repository.language,
            "languages": repository.get_languages(),
            "created_at": repository.created_at.strftime("%Y-%m-%d"),
            "updated_at": repository.updated_at.strftime("%Y-%m-%d"),
            "size": repository.size,
            "default_branch": repository.default_branch,
            "has_wiki": repository.has_wiki,
            "has_issues": repository.has_issues,
            "license": repository.license.name if repository.license else "No license",
            "topics": repository.get_topics(),
        }
        
        # Get README content
        try:
            readme = repository.get_readme()
            repo_data["readme_size"] = readme.size
            repo_data["has_readme"] = True
        except:
            repo_data["has_readme"] = False
            repo_data["readme_size"] = 0
        
        # Get recent commits count
        try:
            commits = repository.get_commits()
            repo_data["total_commits"] = commits.totalCount
        except:
            repo_data["total_commits"] = 0
        
        # Get contributors count
        try:
            contributors = repository.get_contributors()
            repo_data["contributors_count"] = contributors.totalCount
        except:
            repo_data["contributors_count"] = 0
        
        # Check for CI/CD files
        try:
            contents = repository.get_contents("")
            file_names = [content.name for content in contents]
            repo_data["has_ci_cd"] = any(f in file_names for f in ['.github', '.travis.yml', 'Jenkinsfile', '.gitlab-ci.yml'])
            repo_data["has_tests"] = any('test' in f.lower() for f in file_names)
            repo_data["has_docker"] = 'Dockerfile' in file_names or 'docker-compose.yml' in file_names
        except:
            repo_data["has_ci_cd"] = False
            repo_data["has_tests"] = False
            repo_data["has_docker"] = False
        
        return repo_data
    
    except Exception as e:
        print(f"Error fetching repo data: {e}")
        return None

def github_agent(state: State):
    """GitHub repository analyzer agent"""
    
    # Get the last user message
    last_message = state["messages"][-1]
    if isinstance(last_message, dict):
        user_content = last_message.get("content")
    else:
        user_content = last_message.content
    
    # Extract GitHub URL
    github_url, owner, repo = extract_github_url(user_content)
    
    if not github_url:
        return {"messages": [{"role": "assistant", "content": "Please provide a valid GitHub repository URL (e.g., https://github.com/owner/repo)"}]}
    
    # Fetch repository data
    repo_data = fetch_repo_data(owner, repo)
    
    if not repo_data:
        return {"messages": [{"role": "assistant", "content": f"❌ Unable to fetch data for repository: {github_url}\n\nPlease check if:\n- The repository exists\n- The repository is public\n- Your GitHub token has proper permissions"}]}
    
    # Create detailed context for LLM
    repo_context = f"""
Repository: {repo_data['full_name']}
Description: {repo_data['description'] or 'No description'}
Primary Language: {repo_data['language'] or 'Not specified'}
Languages Used: {', '.join(repo_data['languages'].keys())}

📊 Repository Stats:
- ⭐ Stars: {repo_data['stars']}
- 🍴 Forks: {repo_data['forks']}
- 🐛 Open Issues: {repo_data['open_issues']}
- 👥 Contributors: {repo_data['contributors_count']}
- 📝 Total Commits: {repo_data['total_commits']}
- 📅 Created: {repo_data['created_at']}
- 🔄 Last Updated: {repo_data['updated_at']}
- 📦 Size: {repo_data['size']} KB

📋 Repository Features:
- README: {'✅ Yes' if repo_data['has_readme'] else '❌ No'} ({repo_data['readme_size']} bytes)
- License: {repo_data['license']}
- CI/CD: {'✅ Yes' if repo_data['has_ci_cd'] else '❌ No'}
- Tests: {'✅ Yes' if repo_data['has_tests'] else '❌ No'}
- Docker: {'✅ Yes' if repo_data['has_docker'] else '❌ No'}
- Topics: {', '.join(repo_data['topics']) if repo_data['topics'] else 'None'}
"""

    system_prompt = f"""You are an expert code reviewer and GitHub repository analyzer. 

Based on the following repository data, analyze and rate it on these 10 categories (1-10 scale):

{repo_context}

Rate the repository on:

1. **codeQuality** (1-10): Code readability, maintainability, language usage
2. **rigorReliability** (1-10): Testing presence, commit frequency, issue management
3. **architectureScalability** (1-10): Repository structure, modularity
4. **operationalAwareness** (1-10): CI/CD, Docker, deployment readiness
5. **documentation** (1-10): README quality, documentation completeness
6. **apiDesign** (1-10): Project structure and organization
7. **dependencyManagement** (1-10): Language ecosystem, package management
8. **security** (1-10): License presence, security practices
9. **stateManagement** (1-10): Project maintenance and update frequency
10. **codeReviewReadiness** (1-10): Overall code quality indicators

Format your response as(do not include any explanations):

🔍 **GitHub Repository Analysis**

**Repository**: {repo_data['full_name']}
**URL**: {github_url}

**Scores:**
- Code Quality: X/10
- Rigor & Reliability: X/10 
- Architecture & Scalability: X/10 
- Operational Awareness: X/10 
- Documentation: X/10 
- API Design: X/10 
- Dependency Management: X/10 
- Security: X/10 
- State Management: X/10 
- Code Review Readiness: X/10 

**Overall Grade: X/10**
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Add just the current user message for analysis
    messages.append({"role": "user", "content": f"Please analyze this GitHub repository: {github_url}"})
    
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}
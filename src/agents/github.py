from langchain.chat_models import init_chat_model
from src.models.schemas import State
from src.config.settings import settings
from github import Github
import re
from difflib import SequenceMatcher

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

def extract_owner_and_repo(text: str) -> tuple:
    """Extract owner and repo from natural language input
    Examples: 
    - "repo Freelance-web by mohitjoer"
    - "repo of mohitjoer and repo name gose by the name of freelance-web"
    - "owner is torvalds and repo is linux"
    - "get me data on the repo Freelance-web by mohitjoer"
    """
    # Pattern 1: "repo <name> by <owner>" or "data on the repo <name> by <owner>"
    repo_by_owner_pattern = r'repo\s+(@?[\w-]+)\s+by\s+(@?[\w-]+)'
    match = re.search(repo_by_owner_pattern, text, re.IGNORECASE)
    if match:
        repo = match.group(1).lstrip('@')
        owner = match.group(2).lstrip('@')
        return owner, repo
    
    # Pattern 2: "owner ... is/of <owner> ... repo ... is/name ... <repo>"
    owner_repo_pattern = r'(?:owner|user|author)(?:\s+\w+)*?\s+(?:is|of|=)\s+(@?[\w-]+)(?:.*?)(?:repo|repository)(?:\s+\w+)*?\s+(?:is|name|=|called|by\s+the\s+name\s+of)\s+(@?[\w-]+)'
    match = re.search(owner_repo_pattern, text, re.IGNORECASE)
    if match:
        owner = match.group(1).lstrip('@')
        repo = match.group(2).lstrip('@')
        return owner, repo
    
    # Pattern 3: "repo of <owner>/<repo>" or "repo of <owner> repo <repo>"
    owner_slash_repo_pattern = r'repo\s+(?:of\s+)?(@?[\w-]+)[/\s]+(@?[\w-]+)'
    match = re.search(owner_slash_repo_pattern, text, re.IGNORECASE)
    if match:
        owner = match.group(1).lstrip('@')
        repo = match.group(2).lstrip('@')
        return owner, repo
    
    # Pattern 4: Look for common keywords and extract last two valid words
    common_words = {'repo', 'repository', 'owner', 'user', 'author', 'of', 'is', 'the', 'and', 'a', 'an', 'name', 'called', 'by', 'please', 'analyze', 'check', 'look', 'at', 'fetch', 'get', 'show', 'github', 'data', 'me', 'on', 'for', 'about'}
    words = text.split()
    valid_words = []
    for word in words:
        clean_word = word.lstrip('@').rstrip('.,!?;:')
        if re.match(r'^[\w-]+$', clean_word) and clean_word.lower() not in common_words:
            valid_words.append(clean_word)
    
    if len(valid_words) >= 2:
        # Return last two valid words as owner and repo
        return valid_words[-2], valid_words[-1]
    elif len(valid_words) == 1:
        return None, valid_words[0]
    
    return None, None

def search_user_repos(owner: str, partial_repo_name: str):
    """Search all public repos of a user and find the most related one
    
    Args:
        owner: GitHub username
        partial_repo_name: Partial or full repository name to match
    
    Returns:
        Matched repository object or None
    """
    try:
        g = Github(settings.GITHUB_TOKEN)
        user = g.get_user(owner)
        
        # Get all public repositories
        repos = user.get_repos(type="public")
        
        best_match = None
        best_score = 0
        
        for repo in repos:
            # Calculate similarity score using SequenceMatcher
            similarity = SequenceMatcher(None, partial_repo_name.lower(), repo.name.lower()).ratio()
            
            if similarity > best_score:
                best_score = similarity
                best_match = repo
        
        # Only return if similarity score is reasonable (> 0.4 threshold)
        if best_match and best_score > 0.4:
            return best_match
        
        return None
    
    except Exception as e:
        print(f"Error searching user repos: {e}")
        return None

def fetch_repo_data(owner: str, repo: str, search_fallback: bool = True):
    """Fetch repository data using GitHub API
    
    Args:
        owner: GitHub username
        repo: Repository name
        search_fallback: If True, search all repos when specific repo not found
    
    Returns:
        Dictionary with repo data or None
    """
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
        error_msg = str(e)
        
        # If repo not found and fallback is enabled, search all repos
        if search_fallback and ("404" in error_msg or "Not Found" in error_msg):
            print(f"Repository '{repo}' not found. Searching all public repos for '{owner}'...")
            matched_repo = search_user_repos(owner, repo)
            
            if matched_repo:
                print(f"Found similar repo: {matched_repo.name}")
                # Recursively call fetch_repo_data with the matched repo, but disable fallback
                return fetch_repo_data(owner, matched_repo.name, search_fallback=False)
        
        print(f"Error fetching repo data: {e}")
        return None

def github_agent(state: State):
    """GitHub repository analyzer agent"""
    
    # Check if GitHub token is configured
    if not settings.GITHUB_TOKEN:
        return {"messages": [{"role": "assistant", "content": "❌ GitHub token is not configured. Please set the GITHUB_TOKEN environment variable."}]}
    
    # Get the last user message
    last_message = state["messages"][-1]
    if isinstance(last_message, dict):
        user_content = last_message.get("content")
    else:
        user_content = last_message.content
    
    # If classifier provided identifiers, use them
    owner = state.get("username") or None
    repo = state.get("repo_name") or None

    # Extract GitHub URL first (may overwrite owner/repo if URL present)
    github_url, url_owner, url_repo = extract_github_url(user_content)
    if url_owner and url_repo:
        owner, repo = url_owner, url_repo
    
    # If no URL found, try to extract from natural language
    if not github_url and (not owner or not repo):
        owner, repo = extract_owner_and_repo(user_content)
        if not owner or not repo:
            return {"messages": [{"role": "assistant", "content": "Please provide a valid GitHub repository URL (e.g., https://github.com/owner/repo) or mention the owner and repository name clearly (e.g., 'get info on mohitjoer/freelance-web' or 'repo of mohitjoer and repo name freelance-web')"}]}
    
    # Fetch repository data (with fallback search enabled)
    repo_data = fetch_repo_data(owner, repo, search_fallback=True)
    
    if not repo_data:
        repo_ref = github_url if github_url else f"{owner}/{repo}"
        # Try to provide helpful suggestions
        try:
            g = Github(settings.GITHUB_TOKEN)
            user_obj = g.get_user(owner)
            repos = list(user_obj.get_repos(type="public"))
            
            if repos:
                repo_list = "\n- ".join([r.name for r in repos[:10]])
                suggestions = f"\n\n💡 **Available repositories for {owner}:**\n- {repo_list}"
                if len(repos) > 10:
                    suggestions += f"\n... and {len(repos) - 10} more"
            else:
                suggestions = f"\n\n💡 No public repositories found for user '{owner}'"
        except Exception as e:
            suggestions = f"\n\n💡 Unable to list repositories: {str(e)}"
        
        return {"messages": [{"role": "assistant", "content": f"❌ Unable to fetch data for repository: {repo_ref}\n\nPlease check if:\n- The repository name is correct (you provided: '{repo}')\n- The owner name is correct (you provided: '{owner}')\n- The repository is public\n- Your GitHub token has proper permissions{suggestions}"}]}
    
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
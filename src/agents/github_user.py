from langchain.chat_models import init_chat_model
from src.models.schemas import State
from src.config.settings import settings
from github import Github
from datetime import datetime, UTC
import re

llm = init_chat_model(settings.LLM_MODEL)

def extract_github_username(text: str) -> str:
    """Extract GitHub username from text or URL"""
    # Match full URL pattern
    url_pattern = r'https?://github\.com/([\w-]+)(?:/|$)'
    url_match = re.search(url_pattern, text)
    if url_match:
        return url_match.group(1)
    
    # Look for "user <username>" pattern, skipping filler words like "name", "account", etc.
   
    user_pattern = r'(?:user|username|profile)(?:\s+(?:name|account|id|of|for))*\s+(@?[\w-]+)'
    user_match = re.search(user_pattern, text, re.IGNORECASE)
    if user_match:
        return user_match.group(1).lstrip('@')
    
    # Look for @username pattern
    at_pattern = r'@([\w-]+)'
    at_match = re.search(at_pattern, text)
    if at_match:
        return at_match.group(1)
    
    # Last resort: extract the last valid username-like word (not common words)
    common_words = {'can', 'you', 'get', 'data', 'on', 'the', 'a', 'an', 'is', 'are', 'for', 'from', 'to', 'with', 'by', 'of', 'in', 'at', 'or', 'and', 'but', 'if', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'analyze', 'check', 'show', 'tell', 'give', 'provide', 'fetch', 'pull', 'get', 'find', 'search', 'look', 'github', 'profile', 'user', 'username', 'account', 'info', 'information', 'details', 'stats', 'statistics', 'name', 'me', 'about', 'help'}
    words = text.split()
    for word in reversed(words):
        clean_word = word.lstrip('@').rstrip('.,!?;:')
        if re.match(r'^[\w-]+$', clean_word) and clean_word.lower() not in common_words:
            return clean_word
    
    return None

def fetch_user_data(username: str):
    """Fetch comprehensive user data from GitHub API"""
    try:
        g = Github(settings.GITHUB_TOKEN)
        user = g.get_user(username)
        
        # Basic profile information
        user_data = {
            "profile": {
                "name": user.name or "Not provided",
                "username": user.login,
                "bio": user.bio or "No bio",
                "company": user.company or "Not provided",
                "location": user.location or "Not provided",
                "website": user.blog or "Not provided",
                "email": user.email or "Not public",
                "followers": user.followers,
                "following": user.following,
                "public_repos": user.public_repos,
                "public_gists": user.public_gists,
                "created_at": user.created_at.strftime("%Y-%m-%d"),
                "updated_at": user.updated_at.strftime("%Y-%m-%d"),
                "twitter_username": user.twitter_username or "Not provided",
                "avatar_url": user.avatar_url,
                "hireable": user.hireable,
                "type": user.type,
            },
            "repositories": [],
            "languages": {},
            "topics": [],
            "contribution_stats": {
                "total_stars": 0,
                "total_forks": 0,
                "total_commits": 0,
                "total_issues": 0,
                "total_prs": 0,
            },
            "organizations": [],
        }
        
        # Fetch organizations
        try:
            orgs = user.get_orgs()
            for org in orgs:
                user_data["organizations"].append({
                    "name": org.login,
                    "description": org.description or "No description",
                })
        except:
            pass
        
        # Fetch repositories
        repos = user.get_repos(type='owner', sort='updated')
        repo_count = 0
        max_repos = 20  # Limit to avoid API rate limits
        
        for repo in repos:
            if repo_count >= max_repos:
                break
            
            try:
                repo_info = {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description or "No description",
                    "url": repo.html_url,
                    "created_at": repo.created_at.strftime("%Y-%m-%d"),
                    "updated_at": repo.updated_at.strftime("%Y-%m-%d"),
                    "pushed_at": repo.pushed_at.strftime("%Y-%m-%d") if repo.pushed_at else "Never",
                    "language": repo.language or "Not specified",
                    "forks": repo.forks_count,
                    "open_issues": repo.open_issues_count,
                    "size": repo.size,
                    "license": repo.license.name if repo.license else "No license",
                    "topics": repo.get_topics(),
                    "is_fork": repo.fork,
                    "default_branch": repo.default_branch,
                    "has_wiki": repo.has_wiki,
                    "has_issues": repo.has_issues,
                }
                
                # Get languages for this repo
                try:
                    repo_languages = repo.get_languages()
                    repo_info["languages"] = repo_languages
                    
                    # Aggregate languages
                    for lang, bytes_count in repo_languages.items():
                        if lang in user_data["languages"]:
                            user_data["languages"][lang] += bytes_count
                        else:
                            user_data["languages"][lang] = bytes_count
                except:
                    repo_info["languages"] = {}
                
                # Aggregate topics
                for topic in repo_info["topics"]:
                    if topic not in user_data["topics"]:
                        user_data["topics"].append(topic)
                
                # Aggregate stats
                user_data["contribution_stats"]["total_stars"] += repo.stargazers_count
                user_data["contribution_stats"]["total_forks"] += repo.forks_count
                user_data["contribution_stats"]["total_issues"] += repo.open_issues_count
                
                user_data["repositories"].append(repo_info)
                repo_count += 1
                
            except Exception as e:
                print(f"Error fetching repo {repo.name}: {e}")
                continue
        
        # Sort languages by usage
        user_data["languages"] = dict(sorted(
            user_data["languages"].items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        return user_data
    
    except Exception as e:
        print(f"Error fetching user data: {e}")
        return None

def github_user_agent(state: State):
    """GitHub user profile analyzer agent"""
    
    # Get the last user message
    last_message = state["messages"][-1]
    if isinstance(last_message, dict):
        user_content = last_message.get("content")
    else:
        user_content = last_message.content
    
    # Extract GitHub username
    username = extract_github_username(user_content)
    
    if not username:
        return {"messages": [{"role": "assistant", "content": "Please provide a valid GitHub username or profile URL (e.g., `octocat` or `https://github.com/octocat`)"}]}
    
    # Fetch user data
    user_data = fetch_user_data(username)
    
    if not user_data:
        return {"messages": [{"role": "assistant", "content": f"❌ Unable to fetch data for GitHub user: **{username}**\n\nPlease check if:\n- The username is correct\n- The profile is public\n- Your GitHub token has proper permissions"}]}
    
    # Create profile context
    profile = user_data["profile"]
    
    # Top languages
    top_languages = list(user_data["languages"].keys())[:10]
    
    # Build detailed context
    profile_context = f"""
# GitHub User Profile Data

## Profile Information
- **Name**: {profile['name']}
- **Username**: @{profile['username']}
- **Bio**: {profile['bio']}
- **Company**: {profile['company']}
- **Location**: {profile['location']}
- **Website**: {profile['website']}
- **Email**: {profile['email']}
- **Twitter**: {profile['twitter_username']}
- **Hireable**: {'Yes' if profile['hireable'] else 'No/Unknown'}
- **Account Created**: {profile['created_at']}
- **Last Updated**: {profile['updated_at']}

## Social Stats
- **Followers**: {profile['followers']}
- **Following**: {profile['following']}
- **Public Repos**: {profile['public_repos']}
- **Public Gists**: {profile['public_gists']}

## Contribution Stats
- **Total Forks**: {user_data['contribution_stats']['total_forks']}
- **Total Open Issues**: {user_data['contribution_stats']['total_issues']}

## Languages Used (by code volume)
{', '.join(top_languages) if top_languages else 'No languages detected'}

## Topics/Skills
{', '.join(user_data['topics'][:20]) if user_data['topics'] else 'No topics'}

## Organizations
{', '.join([org['name'] for org in user_data['organizations']]) if user_data['organizations'] else 'No public organizations'}

---

**ANALYSIS GUIDELINES:**
- Be direct and specific—avoid generic statements
- Support every claim with evidence from the data
- Use bullet points for clarity, not paragraphs
- Focus on insights that matter for hiring/collaboration decisions

**OUTPUT FORMAT:**

# 🎯 Developer Profile: @{profile['username']}

## ⚡ Quick Summary
> One-liner capturing their developer identity and value proposition.

## 🛠️ Tech Stack Mastery
| Skill | Proficiency | Evidence |
|-------|-------------|----------|
(Top 5 skills only, with concrete repo/contribution evidence)

## 📊 Developer DNA
- **Archetype**: [e.g., "Full-Stack Builder", "Open Source Contributor", "Framework Specialist"]
- **Experience Signal**: [Junior/Mid/Senior/Staff based on evidence]
- **Activity Pattern**: [Active/Moderate/Dormant + context]
- **Code Quality Indicators**: [Based on stars, forks, documentation presence]

**RULES:**
- Maximum 200 words total
- No fluff or filler phrases
- Every section must add unique value
- Skip sections if data is insufficient (don't fabricate)"""

    system_prompt = profile_context
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": f"Analyze this GitHub user's profile: {username}"})
    
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}
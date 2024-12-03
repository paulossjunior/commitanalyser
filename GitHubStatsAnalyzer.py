import requests
from datetime import datetime
import pandas as pd
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO

class GitHubStatsAnalyzer:
    def __init__(self, owner, repo):
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {"Accept": "application/vnd.github.v3+json"}

    def get_repository_info(self):
        """Get basic repository information."""
        response = requests.get(self.base_url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def get_branch_stats(self):
        """Get statistics about all branches."""
        branches_url = f"{self.base_url}/branches"
        response = requests.get(branches_url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch branches: {response.status_code}")
            
        branches = response.json()
        return {
            "total_branches": len(branches),
            "branch_names": [branch["name"] for branch in branches],
            "protected_branches": sum(1 for branch in branches if branch.get("protected", False))
        }

    def get_commit_stats(self, branch="main"):
        """Get commit statistics for a specific branch."""
        commits_url = f"{self.base_url}/commits"
        params = {"sha": branch, "per_page": 100}
        
        all_commits = []
        page = 1
        
        while True:
            params["page"] = page
            response = requests.get(commits_url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                break
                
            commits = response.json()
            if not commits:
                break
                
            all_commits.extend(commits)
            page += 1
            
            if len(all_commits) >= 500:
                break

        return self._analyze_commits(all_commits)

    def _analyze_commits(self, commits):
        """Analyze commit data and generate statistics."""
        stats = {
            "total_commits": len(commits),
            "authors": defaultdict(int),
            "commits_by_month": defaultdict(int),
            "commits_by_day": defaultdict(int),
            "commits_by_weekday": defaultdict(int),
            "avg_commits_per_day": 0
        }

        dates = []
        
        for commit in commits:
            author = commit["commit"]["author"]["name"]
            stats["authors"][author] += 1
            
            date = datetime.strptime(commit["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ")
            month_key = date.strftime("%Y-%m")
            day_key = date.strftime("%Y-%m-%d")
            weekday = date.strftime("%A")
            
            stats["commits_by_month"][month_key] += 1
            stats["commits_by_day"][day_key] += 1
            stats["commits_by_weekday"][weekday] += 1
            dates.append(date)

        if dates:
            date_range = (max(dates) - min(dates)).days + 1
            stats["avg_commits_per_day"] = len(commits) / date_range
            stats["date_range"] = {"start": min(dates), "end": max(dates)}

        return stats

    def _create_contributors_chart(self, commit_stats):
        """Create a bar chart for top contributors."""
        plt.figure(figsize=(10, 6))
        authors = dict(sorted(commit_stats["authors"].items(), key=lambda x: x[1], reverse=True)[:10])
        plt.bar(authors.keys(), authors.values())
        plt.xticks(rotation=45, ha='right')
        plt.title('Top 10 Contributors')
        plt.tight_layout()
        
        img = BytesIO()
        plt.savefig(img, format='png')
        plt.close()
        return base64.b64encode(img.getvalue()).decode()

    def _create_commits_by_weekday_chart(self, commit_stats):
        """Create a bar chart for commits by weekday."""
        plt.figure(figsize=(10, 6))
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        commits = [commit_stats["commits_by_weekday"].get(day, 0) for day in weekdays]
        plt.bar(weekdays, commits)
        plt.xticks(rotation=45, ha='right')
        plt.title('Commits by Weekday')
        plt.tight_layout()
        
        img = BytesIO()
        plt.savefig(img, format='png')
        plt.close()
        return base64.b64encode(img.getvalue()).decode()

    def generate_markdown_report(self):
        """Generate a comprehensive Markdown report."""
        try:
            repo_info = self.get_repository_info()
            branch_stats = self.get_branch_stats()
            commit_stats = self.get_commit_stats()
            
            # Generate charts
            contributors_chart = self._create_contributors_chart(commit_stats)
            weekday_chart = self._create_commits_by_weekday_chart(commit_stats)
            
            report = f"""# GitHub Repository Analysis Report
## {self.owner}/{self.repo}

### Repository Overview
- **Description**: {repo_info.get('description', 'No description available')}
- **Stars**: {repo_info.get('stargazers_count', 0):,}
- **Forks**: {repo_info.get('forks_count', 0):,}
- **Open Issues**: {repo_info.get('open_issues_count', 0):,}
- **Created**: {repo_info.get('created_at', 'N/A')}
- **Last Updated**: {repo_info.get('updated_at', 'N/A')}

### Branch Statistics
- **Total Branches**: {branch_stats['total_branches']}
- **Protected Branches**: {branch_stats['protected_branches']}

#### Branch List
{chr(10).join(['- ' + branch for branch in branch_stats['branch_names']])}

### Commit Statistics
- **Total Commits Analyzed**: {commit_stats['total_commits']:,}
- **Average Commits per Day**: {commit_stats['avg_commits_per_day']:.2f}
- **Analysis Period**: {commit_stats['date_range']['start'].strftime('%Y-%m-%d')} to {commit_stats['date_range']['end'].strftime('%Y-%m-%d')}

### Top Contributors
![Top Contributors](data:image/png;base64,{contributors_chart})

### Commits by Weekday
![Commits by Weekday](data:image/png;base64,{weekday_chart})

### Monthly Commit Activity
| Month | Commits |
|-------|---------|
{chr(10).join([f"| {month} | {commits} |" for month, commits in sorted(commit_stats['commits_by_month'].items(), reverse=True)[:6]])}

### Additional Information
- Repository URL: https://github.com/{self.owner}/{self.repo}
- Analysis Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
*This report was generated automatically using GitHubStatsAnalyzer*
"""
            return report
            
        except Exception as e:
            return f"# Error Generating Report\nAn error occurred: {str(e)}"

# Example usage
if __name__ == "__main__":
    analyzer = GitHubStatsAnalyzer("microsoft", "vscode")
    markdown_report = analyzer.generate_markdown_report()
    
    # Save to file
    with open('github_report.md', 'w') as f:
        f.write(markdown_report)
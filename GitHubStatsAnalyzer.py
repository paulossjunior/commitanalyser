import requests
from datetime import datetime
import matplotlib.pyplot as plt
import json
import os
from collections import defaultdict
from pathlib import Path

class GitHubAnalyzer:
    def __init__(self, config_file):
        self.config = self._load_config(config_file)
        self.output_dir = Path(self.config.get('output_directory', 'reports'))
        self.output_dir.mkdir(exist_ok=True)

    def _load_config(self, config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            if 'repositories' not in config:
                raise ValueError("Missing 'repositories' list in config")
            return config
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            raise

    def get_repo_data(self, owner, repo):
        """Get all repository data in one function"""
        try:
            # Get basic repo info
            repo_url = f"https://api.github.com/repos/{owner}/{repo}"
            repo_response = requests.get(repo_url)
            if repo_response.status_code != 200:
                print(f"Failed to get repo info: {repo_response.status_code}")
                return None
            repo_info = repo_response.json()

            # Get commits
            commits = []
            page = 1
            while page <= 5:  # Limit to 5 pages
                commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
                commits_response = requests.get(commits_url, params={'page': page, 'per_page': 100})
                if commits_response.status_code != 200 or not commits_response.json():
                    break
                commits.extend(commits_response.json())
                page += 1

            # Get branches
            branches_url = f"https://api.github.com/repos/{owner}/{repo}/branches"
            branches_response = requests.get(branches_url)
            branches = branches_response.json() if branches_response.status_code == 200 else []

            return {
                'repo_info': repo_info,
                'commits': commits,
                'branches': branches
            }
        except Exception as e:
            print(f"Error getting data for {owner}/{repo}: {str(e)}")
            return None

    def analyze_commits(self, commits):
        stats = {
            'total_commits': len(commits),
            'authors': defaultdict(int),
            'commits_by_date': defaultdict(int)
        }

        for commit in commits:
            if not commit.get('commit'):
                continue
                
            author = commit['commit'].get('author', {})
            if not author:
                continue

            name = author.get('name', 'Unknown')
            date = author.get('date', '')[:10]
            
            stats['authors'][name] += 1
            stats['commits_by_date'][date] += 1

        stats['authors'] = dict(sorted(
            stats['authors'].items(), 
            key=lambda x: x[1], 
            reverse=True
        ))

        return stats

    def create_commit_graph(self, stats, filepath):
        plt.figure(figsize=(12, 6))
        
        authors = list(stats['authors'].keys())[:10]
        commits = [stats['authors'][author] for author in authors]
        
        plt.bar(authors, commits)
        plt.xticks(rotation=45, ha='right')
        plt.title('Top Contributors')
        plt.tight_layout()
        
        plt.savefig(filepath)
        plt.close()

    def analyze_repository(self, repo_info):
        """Analyze a single repository"""
        owner = repo_info['owner']
        repo_name = repo_info['name']
        
        print(f"Analyzing repository: {owner}/{repo_name}")
        
        # Create repository directory
        repo_dir = self.output_dir / f"{owner}_{repo_name}"
        repo_dir.mkdir(exist_ok=True)
        
        # Get repository data
        data = self.get_repo_data(owner, repo_name)
        if not data:
            print(f"Failed to get data for {owner}/{repo_name}")
            return None
        
        # Analyze commits
        commit_stats = self.analyze_commits(data['commits'])
        
        # Create and save graph
        graph_path = repo_dir / 'contributors_graph.png'
        self.create_commit_graph(commit_stats, graph_path)
        
        # Generate report
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report_content = f"""# GitHub Repository Analysis: {owner}/{repo_name}
Generated on: {timestamp}

## Repository Information
- Stars: {data['repo_info'].get('stargazers_count', 0)}
- Forks: {data['repo_info'].get('forks_count', 0)}
- Open Issues: {data['repo_info'].get('open_issues_count', 0)}
- Created: {data['repo_info'].get('created_at', 'N/A')}
- Last Updated: {data['repo_info'].get('updated_at', 'N/A')}

## Branch Information
- Total Branches: {len(data['branches'])}
- Branch Names: {', '.join(b['name'] for b in data['branches'])}

## Commit Analysis
- Total Commits Analyzed: {commit_stats['total_commits']}

### Top Contributors
"""
        
        # Add top contributors
        for author, count in list(commit_stats['authors'].items())[:10]:
            report_content += f"- {author}: {count} commits\n"
        
        # Add graph reference
        report_content += "\n## Contribution Graph\n"
        report_content += "![Contributors Graph](contributors_graph.png)\n"
        
        # Save report
        report_file = repo_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_file.write_text(report_content)
        
        print(f"Report generated for {owner}/{repo_name}: {report_file}")
        return report_file

    def analyze_all_repositories(self):
        """Analyze all repositories from config"""
        print(f"Starting analysis of {len(self.config['repositories'])} repositories...")
        
        reports = []
        for repo in self.config['repositories']:
            try:
                report_file = self.analyze_repository(repo)
                if report_file:
                    reports.append(report_file)
            except Exception as e:
                print(f"Error analyzing {repo.get('owner', '')}/{repo.get('name', '')}: {str(e)}")
        
        if reports:
            # Create summary report
            summary_file = self.output_dir / f"analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            summary_content = "# GitHub Repository Analysis Summary\n\n"
            summary_content += f"Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            summary_content += "## Generated Reports\n\n"
            
            for report in reports:
                repo_name = report.parent.name
                summary_content += f"- [{repo_name}]({report.name})\n"
            
            summary_file.write_text(summary_content)
            reports.append(summary_file)
        
        return reports

if __name__ == "__main__":
    try:
        analyzer = GitHubAnalyzer('config.json')
        reports = analyzer.analyze_all_repositories()
        print(f"\nAnalysis completed. Generated {len(reports)} reports.")
    except Exception as e:
        print(f"Error: {str(e)}")
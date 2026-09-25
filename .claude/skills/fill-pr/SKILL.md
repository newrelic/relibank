---
name: fill-pr
description: Automatically fills out the repository's pull request template using git diffs, commit history, interactive testing questions, and optionally creates/pushes the PR on GitHub.
---

# Pull Request Auto-Filler Skill

## Objective
Generate a completed PR description by reading the project's actual PR template file, analyzing local git context, interviewing the user for testing/evidence details, and optionally pushing and submitting the PR via GitHub CLI (`gh`).

---

## Instructions

1. **Locate PR Template**
   - Check the root directory or `.github/` folder for `PULL_REQUEST_TEMPLATE.md` (or `.github/PULL_REQUEST_TEMPLATE.md`).
   - Read the exact file content so you use the latest live version as your structural blueprint.

2. **Gather Repository Context**
   - Run `git status`, `git log origin/main..HEAD`, and `git diff origin/main..HEAD` to evaluate all code changes.
   - Look for ticket references (e.g., `JIRA-123`, `GH-456`) in branch names or commit messages.

3. **Interactive Testing & Evidence Discussion**
   - Ask concise questions to populate sections **3 (Testing)** and **4 (Evidence)**:
     1. **Environment & Safety:** What environment was tested (e.g., Local, Staging), why is this safe for production, and are there any intentionally untested areas?
     2. **Scenarios (Coverage Table):** Briefly describe the primary Happy Path outcome and any Edge Cases tested (with results).
     3. **Evidence:** Are there screenshot links, log snippets, or test reports to include, or should these be marked as N/A?

4. **Populate and Present Output**
   - Combine the git context and user responses to populate the template loaded in Step 1.
   - **PR Type:** Select the single appropriate checkbox (`[x]`).
   - **Ticket Reference:** Fill in detected ticket IDs/URLs or leave placeholders if unavailable.
   - **Summary & Justifications:** Describe the primary goal, expected outcome, and break down significant changes with technical justifications based on the diff.
   - **Testing, Safety & Evidence:** Map user responses into the Testing Strategy, Coverage Table, and Evidence sections.
   - **Checklist:** Pre-check (`[x]`) items verified by repository state.
   - **Always display the fully populated PR description inside a clear Markdown code block for user review.**

5. **PR Submission Prompt & Execution**
   - After displaying the Markdown, ask the user if they would like you to automatically push the branch and open the PR on GitHub.
   - **If the user confirms:**
     1. Push the current branch to origin: `git push -u origin HEAD`
     2. Create the pull request using GitHub CLI:
        ```bash
        gh pr create --title "<PR_TITLE>" --body-file - << 'EOF'
        <INSERT_COMPLETED_PR_MARKDOWN>
        EOF
        ```
     3. Output the returned PR URL.
   - **If the user declines:** End the process so they can copy/paste the generated template manually.

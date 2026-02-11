🚀 Pull Request
========================

🎯 PR Type
----------
-   [ ] **Feature:** Adds new functionality or user-facing change.
-   [ ] **Bug Fix:** Solves a defect or incorrect behavior.
-   [ ] **Refactor:** Improves code structure/readability without changing external behavior.
-   [ ] **Documentation:** Updates to README, Wiki, or internal docs.
-   [ ] **Chore:** Non-code changes (e.g., CI configuration, dependency bumps).

1\. Issue Tracking & Reference
------------------------------
-   **Ticket Number(s):** [e.g., JIRA-123, GH-456]
-   **Ticket Link(s):** [Insert direct URL to the issue/ticket here]

2\. Summary of Changes
----------------------
Briefly describe the purpose of this PR. What is the overall goal it achieves?
-   **Expected Outcome:** [What should the user or system see after this PR is merged and deployed? (e.g., "New pricing page goes live," "Latency decreases by 100ms," "Bug X is resolved.")]

### Detailed Change Log & Justification
List each significant change made in this PR. For each, provide a brief justification explaining *why* the change was necessary (e.g., to fix a bug, meet a requirement, or improve performance).
-   **Change 1:** [Description of the change, e.g., "Updated `UserController.js` to handle null user inputs."]
    -   **Justification:** [e.g., "This prevents a server crash when a user submits an empty form."]
-   **Change 2:** [Description of the change]
    -   **Justification:** [Explanation of why this change was made]

3\. Testing
-----------
Describe how you tested this PR. The quality of testing directly impacts the speed of review and deployment.

Run the test suite locally with this in-development branch, and upload the results. If new tests are required, like for new features, add those tests and call them out here.
```cd tests && ./run_tests.sh > ../../test_results.txt```

### Testing Strategy
-   **Environment Used:** (e.g., Local, Sandbox, Staging)
-   **Production Safety Assessment:** [Why do you believe this change is safe to deploy to production? (e.g., "Covered by comprehensive unit and integration tests," "It's an idempotent, non-breaking change," "Only touches static asset files.")]
-   **What areas were NOT tested and why?** (e.g., "Did not test old IE browsers as they are deprecated.")

### Coverage Details

| Scenario      | Details                                                                    | Results                           |
| ------------- | -------------------------------------------------------------------------- | --------------------------------- |
| Happy Path    | [List sequential steps for the primary intended use case.]                 | [Add notes on outcome of testing] |
| Edge Case 1   | [Test boundaries: null values, zero, max limits, concurrent actions, etc.] | [Add notes on outcome of testing] |
| Edge Case ... | [Test boundaries: null values, zero, max limits, concurrent actions, etc.] | [Add notes on outcome of testing] |

4\. Evidence
------------
Provide evidence of successful testing.
-   **Screenshots/Gifs:** [Paste image links or attach screenshots here]
-   **Console/Log Output Snippets:** [Paste relevant logs or links to log files]
-   **Test Report Links:** [Link to test runs, etc.]

_Testing and evidence are **REQUIRED** before requesting review!_

5\. Review and Merge Checklist
------------------------------
Confirm the following prerequisites have been met by checking the boxes:
-   [ ] All blocking review comments from the latest round are **resolved**.
-   [ ] This branch has been rebased against the `main` branch and all **merge conflicts are resolved**.
-   [ ] The code includes sufficient comments, particularly in complex or non-obvious areas.
-   [ ] The code adheres to project **coding standards** (linting, style guides, best practices).
-   [ ] Relevant documentation and runbooks have been updated, if necessary.
-   [ ] My changes generate no new warnings or errors.
-   [ ] My commits are squashed into a single, descriptive commit.
-   [ ] My test results are uploaded as a text file, and new tests were created where required.
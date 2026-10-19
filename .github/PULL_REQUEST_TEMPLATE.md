## Description

<!-- Provide a clear and concise description of the changes in this PR. -->

## Type of Change

<!-- Mark the appropriate option with an "x". -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🔧 Configuration change
- [ ] ♻️ Refactoring (no functional changes)
- [ ] 🧪 Test update
- [ ] 📦 Dependency update

## Testing

<!-- Describe the tests you ran and how to reproduce them. -->

- [ ] Unit tests pass locally (`pytest tests/ -v`)
- [ ] Integration tests pass (if applicable)
- [ ] Manual testing performed (describe below)

### Test Evidence

<!-- Add screenshots, test output, or other evidence. -->

## Checklist

- [ ] My code follows the project's style guidelines (`ruff check src/ tests/`)
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I have updated the README.md / documentation accordingly
- [ ] I have updated `config/default.yaml` if configuration changes were made
- [ ] I have verified the Docker image builds successfully (`docker build .`)

## Database Changes

<!-- If applicable, describe any database schema changes. -->

- [ ] No database changes
- [ ] New migration added (describe: _______)
- [ ] Schema change requires manual migration

## DICOM Compliance

<!-- If applicable, note any DICOM-related considerations. -->

- [ ] No DICOM protocol changes
- [ ] Changes verified against DICOM standard (describe: _______)
- [ ] AE Title, port, or SCP/SCU behavior unchanged

## Additional Notes

<!-- Any additional information that reviewers should know. -->

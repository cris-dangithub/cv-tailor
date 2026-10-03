# cv-tailor workspace

This folder is a **cv-tailor workspace** (config in `.cv-tailor/config.yaml`).

- Always talk to the user in **{{ui_language}}**.
- When the user pastes or links a **job offer** in this folder, with or without saying "generate
  my CV", run the `cv-tailor` skill to generate it, in **{{cv_languages}}**. Several offers in one
  message mean several applications.
- Use the `cv-tailor` skill as well when the user wants to find something they applied to, gives
  feedback on an application, changes its status, or wants a different CV style.
- Never write into the knowledge pool listed in the config: it is read-only.
- If the skill is not auto-discovered, open `{{skill_dir}}/SKILL.md` and follow it.

# cv-tailor workspace

This folder is a **cv-tailor workspace** (config in `.cv-tailor/config.yaml`).

- Always talk to the user in **{{ui_language}}**.
- When the user pastes or links a **job offer** here, with or without asking for it explicitly,
  generate the tailored CV with the `cv-tailor` skill, in **{{cv_languages}}**. Several offers
  in one message mean several applications.
- Use the same skill when the user wants to find a past application, gives feedback on one,
  updates its status, or asks for another CV style.
- The knowledge pool listed in the config is read-only.
- The skill lives at `{{skill_dir}}`. If your agent did not load it automatically, open
  `{{skill_dir}}/SKILL.md` and follow it step by step.

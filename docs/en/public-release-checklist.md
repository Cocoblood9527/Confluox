# Public Release Checklist

Use this checklist before sharing Confluox publicly on GitHub or announcing a meaningful documentation update.

## GitHub Front Door

- [ ] Repository visibility and name are correct
- [ ] GitHub About description is set
- [ ] GitHub topics are set
- [ ] `README.md` renders clearly on the repository home page
- [ ] `README.zh-CN.md` is linked and reachable from the English README
- [ ] `LICENSE` is present and visible
- [ ] `CONTRIBUTING.md` is discoverable from the README
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` is present

## Minimum Local Validation

- [ ] Key README links open the expected docs
- [ ] Documented setup commands still match the repository
- [ ] The shortest local run path still makes sense:
  - [ ] `cd frontend && npm run dev`
  - [ ] `cargo tauri dev`
- [ ] Gateway test command is still documented consistently:
  - [ ] `cd gateway && python -m pytest tests -q`
- [ ] Packaging command is still documented consistently:
  - [ ] `cd gateway && ./scripts/build_gateway.sh --track all`
- [ ] README limitations still describe project maturity honestly
- [ ] Public-facing English and Chinese docs are not obviously out of sync

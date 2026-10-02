# Changelog

## [0.1.1](https://github.com/Endika/madrid-avisos/compare/v0.1.0...v0.1.1) (2026-10-02)


### Bug Fixes

* use pass in protocol bodies so CodeQL stops flagging them ([a5d0754](https://github.com/Endika/madrid-avisos/commit/a5d0754276b35a00d707882176bd4e6d3d385fae))

## 0.1.0 (2026-09-26)


### Features

* push street-cleaning avisos on avisos.madrid.es every morning ([7449258](https://github.com/Endika/madrid-avisos/commit/7449258995e1fdff4b4508bdf786a5f696f99997))


### Bug Fixes

* keep the state private even over a leftover temp file ([ddd2b3d](https://github.com/Endika/madrid-avisos/commit/ddd2b3d9838c6ebb35dd6432893edb7fdc76c05f))
* log Slack's error code instead of its whole reply ([b158eac](https://github.com/Endika/madrid-avisos/commit/b158eac0c3d709ca8501992f587c776e2d3fb848))
* name the closed aviso a dry run would replace ([8259e87](https://github.com/Endika/madrid-avisos/commit/8259e8738014065ee4f6c76f552d6b41a41ef20a))
* refuse a non-object state, keep it private, and read odd Slack replies ([4855321](https://github.com/Endika/madrid-avisos/commit/4855321639b84927cdaec276958b8e59d14e4534))
* report every failure to Slack and never let two streets share an aviso ([e14d43e](https://github.com/Endika/madrid-avisos/commit/e14d43e0b9c7a0bb64a03d05f172736d14f35fbc))


### Documentation

* describe the package layout in the README ([9dbbd1d](https://github.com/Endika/madrid-avisos/commit/9dbbd1d7815d7faf3405544eaf69b56640272f3d))
* say a closed aviso hands over to an open one before a new one ([dcb6470](https://github.com/Endika/madrid-avisos/commit/dcb6470d5b16983af6790886d5c44afdb0d71d23))

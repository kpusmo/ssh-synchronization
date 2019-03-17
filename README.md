# ssh-synchronization
App synchronizes remote server directory with local contents. Copy config-sample.json to config.json, and fill it with real properties.

Modes:
- overwrite - write all files
- update - update existing if date-modified is newer
- add_non_existing - add non-existing files
- update_and_add - update + add_non_existing

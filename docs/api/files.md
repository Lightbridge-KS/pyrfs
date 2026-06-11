# Files — `file_*`

Mutating verbs return the (new) path so calls chain; `overwrite=False` on an
existing target raises `FileExistsError`. Copy/move into an existing directory
targets `dir/basename`.

::: pyrfs.file_create
::: pyrfs.file_touch
::: pyrfs.file_copy
::: pyrfs.file_move
::: pyrfs.file_delete
::: pyrfs.file_exists
::: pyrfs.file_access
::: pyrfs.file_size
::: pyrfs.file_chmod
::: pyrfs.file_chown
::: pyrfs.file_show

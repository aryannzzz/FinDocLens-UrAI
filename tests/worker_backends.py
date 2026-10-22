"""Failure-only test fixtures. These are not extraction model adapters."""


def crash(path, *, context):
    raise RuntimeError('deliberate harness error fixture')


def empty(path, *, context):
    from benchmark.common import sha256
    return dict(document_id='original', source_sha256=sha256(path), input_sha256=sha256(path),
                status='success', tables=[dict(rows=[])], issues=[])


def oom(path, *, context):
    raise MemoryError('deliberate harness OOM fixture')

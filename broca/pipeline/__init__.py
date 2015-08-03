from itertools import product
from broca.pipeline.cryo import Cryo


class Pipeline():
    def __init__(self, *pipes, **kwargs):
        self.freeze = kwargs.get('freeze', True)
        self.refresh = kwargs.get('refresh', False)
        self.cryo = Cryo(refresh=self.refresh)

        # If any of the pipes is a list or a multi-pipeline, we are building multiple pipelines
        if any(isinstance(p, list) or self._is_multi(p) for p in pipes):
            # Coerce all pipes to lists
            c_pipes = []
            for p in pipes:
                if isinstance(p, list):
                    c_pipes.append(p)
                elif self._is_multi(p):
                    c_pipes.append(p.pipelines)
                else:
                    c_pipes.append([p])

            # Build each pipeline
            self.pipelines = [Pipeline(*pipes_) for pipes_ in product(*c_pipes)]

        else:
            self.pipes = pipes

            # Validate the pipeline
            for p_out, p_in in zip(pipes, pipes[1:]):
                if p_out.output != p_in.input:
                    raise Exception('Incompatible: pipe <{}> outputs <{}>, pipe <{}> requires input of <{}>.'.format(
                        type(p_out).__name__, p_out.output,
                        type(p_in).__name__, p_in.input
                    ))

            # So pipelines can be nested
            self.input = self.pipes[0].input
            self.output = self.pipes[-1].output

    def _is_multi(self, pipe):
        return isinstance(pipe, Pipeline) and hasattr(pipe, 'pipelines')

    def __call__(self, input):
        if hasattr(self, 'pipelines'):
            return tuple(p(input) for p in self.pipelines)
        else:
            for pipe in self.pipes:
                output = self.cryo(pipe, input) if self.freeze else pipe(input)
                input = output
            return output

    def __repr__(self):
        if hasattr(self, 'pipelines'):
            return 'MultiPipeline: {}'.format(' || '.join([str(p) for p in self.pipelines]))
        else:
            return ' -> '.join([str(p) for p in self.pipes])


class _PipeType(type):
    _types = {
        'docs': 0,
        'tokens': 1,
        'vecs': 2,
        'sim_mat': 3,
        'assetid_doc': 4, # type == dict,  {asset_id : body_text }
        'assetid_vec': 5 # type == dict,  {asset_id : vec }
    }

    def __getattr__(cls, name):
        if name not in cls._types:
            cls._types[name] = len(cls._types)
        return cls._types[name]

class PipeType(metaclass=_PipeType):
    pass


class Pipe():
    input = None
    output = None
    type = PipeType

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        obj.args = args
        obj.kwargs = kwargs

        # Build Pipe's signature
        args = ', '.join([ags for ags in [
            ', '.join(map(str, args)),
            ', '.join(['{}={}'.format(x, y) for x, y in kwargs.items()])
        ] if ags])
        obj.sig = '{}({})'.format(
            cls.__name__,
            args
        )

        return obj

    def __init__(self, *args, **kwargs):
        self.args = args
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return self.sig

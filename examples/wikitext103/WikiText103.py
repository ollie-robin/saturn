# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================


from examples.wikitext103.models.GPTJ import get_model as getGPTJ, GPTJBlock, GPTJMLP, pretraining_loss

from examples.wikitext103.dataloaders import get_loader
from saturn.core.representations import Task, HParams
from transformers import AutoTokenizer

from examples.wikitext103.executors.FSDP import FSDPExecutor
from examples.wikitext103.executors.Pipeline import PipelineExecutor
from examples.wikitext103.executors.Spilled import SpilledExecutor
import unittest
from saturn.library import register

import torch
from functools import partial
import copy
from saturn.trial_runner.PerformanceEvaluator import search
from saturn import orchestrate


class TestPerformanceEvaluator(unittest.TestCase):
	def setUp(self):
		
		"""
            Configuring hints & tokenizers for the GPT-2 & GPT-J jobs
        """
		
		gptjhints = {"is_transformer": True,
		             "transformer_cls": {GPTJBlock, GPTJMLP}}
		

		gptJTokenizer = AutoTokenizer.from_pretrained(
			"EleutherAI/gpt-j-6B")  # gpt2-xl-medium
		if gptJTokenizer.pad_token is None:
			gptJTokenizer.add_special_tokens({'pad_token': '[PAD]'})
		
		"""
			Registering execution procedures to the library
		"""
		
		self.classes = [FSDPExecutor, PipelineExecutor, SpilledExecutor]
		self.class_names = ["FSDPExecutor",
		                    "PipelineExecutor", "SpilledExecutor"]
		
		for c_name, c in zip(self.class_names, self.classes):
			register(c_name, c)
		
		self.test_tasks = []
		
		"""
			Creating the HPO sweep
		"""
		
		for lr in [1e-5]:
			hparams = HParams(lr=lr, batch_count=500, optimizer_cls=torch.optim.SGD)
			
			self.test_tasks += [
				Task(
					getGPTJ,
					partial(get_loader,
					        16 // (x + 1),
					        split="train",
					        tokenizer=gptJTokenizer,
					        tok_name='gpt-j',
					        full_data=False),
					pretraining_loss,
					hparams=copy.deepcopy(hparams),
					hints=copy.deepcopy(gptjhints),
				) for x in range(2)
			]

	def test(self):
		search(self.test_tasks, log=True)
		batch_2 = copy.deepcopy(self.test_tasks)
		
		
		for b in batch_2:
			b.change_name()
			b.hparams.lr = 1e-3
		
		batch_3 = copy.deepcopy(self.test_tasks)
		for b in batch_3:
			b.change_name()
			b.hparams.lr = 3e-3
		
		self.test_tasks += batch_2
		self.test_tasks += batch_3
		orchestrate(self.test_tasks, log=True)

if __name__ == '__main__':
	unittest.main()
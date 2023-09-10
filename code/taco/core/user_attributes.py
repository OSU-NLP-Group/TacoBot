from dataclasses import dataclass
import logging

import jsonpickle
import json

from taco.core.flags import SIZE_THRESHOLD
from taco.core.util import print_dict_linebyline

logger = logging.getLogger('tacologger')


TMP_DOCUMENT_DATA =  {'documents': {'list_item_selected': {'recipe': {"ingredients": ['Food and Entertaining', 'Recipes', 'Baking', 'Cookies and Biscuits']}}}}

TMP_STEP_DATA =  "Step =  1 Bring a pot of water to boil and cut the paddles into any size you want. Fill a pot that's at least 4 US quarts (3.8 l) in size with water and bring it to a boil over high heat. While the water is heating, cut each of the cactus paddles into pieces or strips. You can slice or cut the cactus paddles into any size you want, but keep the pieces uniform."


@dataclass
class UserAttributes(object):
	user_id: str
	#creation_date_time: str

	@classmethod
	def deserialize(cls, mapping: dict):
		decoded_items = {}
		for k, v in mapping.items():
			try:
				decoded_items[k] = jsonpickle.decode(v)
			except:
				logger.error(f"Unable to decode {k}:{v} from past state")

		constructor_args = ['user_id']
		base_self = cls(**{k: decoded_items[k] for k in constructor_args})
		for k in decoded_items:
			if k not in constructor_args:
				setattr(base_self, k, decoded_items[k])
		return base_self

	def prune_jsons(self):
		"""
		Prune jsons from getting too big
		"""
		for key in self.__dict__.keys():
			res = getattr(self, key)
			ever_successful = False
			if res is None:
				continue
			while True:
				try:
					res = json.loads(res)
				except:
					break
				ever_successful = True
			if ever_successful:
				setattr(self, key, json.dumps(res))

	def serialize(self, logger_print = False):
		logger.debug(f'Running jsonpickle version {jsonpickle.__version__}')
		logger.debug(f'jsonpickle backend names: {jsonpickle.backend.json._backend_names}')
		logger.debug(f'jsonpickle encoder options: {jsonpickle.backend.json._encoder_options}')
		logger.debug(f'jsonpickle fallthrough: {jsonpickle.backend.json._fallthrough}')

		encoded_dict = {k: jsonpickle.encode(v) for k, v in self.__dict__.items()}
		total_size = sum(len(k) + len(v) for k, v in encoded_dict.items())

		if logger_print:
			logger.taco_primary_info('state:\n{}'.format(print_dict_linebyline(self.__dict__)),
								extra={'color_lines_by_component': True})
			
		return encoded_dict


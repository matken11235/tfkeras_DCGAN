# Inside modules
import sys
import time
# Outside modules
import pylab
import numpy as np
import tensorflow as tf
from tensorflow.python.keras import backend as K
from tensorflow.python.training.basic_session_run_hooks import _as_graph_element


class ImageCSListerner(tf.train.CheckpointSaverListener):
	def __init__(self, z, x_pred, output_path):
		# 参照渡しの意
		self.z = z
		self.x_pred = x_pred
		self.output_path = output_path

	def after_save(self, session, global_step_value):
		pylab.rcParams['figure.figsize'] = (16.0, 16.0)
		pylab.clf()
		row = 5
		s = row**2
		feed_z = np.random.uniform(-1, 1, 100 * s).reshape(-1, 100).astype(np.float32)
		x_val = session.run(self.x_pred, feed_dict={self.z: feed_z, K.learning_phase(): False})
		xs = np.reshape(x_val, (-1, 3, 96, 96))
		for i in range(s):
			tmp = xs[i].transpose(1, 2, 0)
			tmp = np.clip(tmp, 0.0, 1.0)
			pylab.subplot(row, row, i+1)
			pylab.imshow(tmp)
			pylab.axis("off")
		filename = "%s/epoch-%s.png" % (self.output_path+"/images", global_step_value)
		tf.logging.info("Plotting image for %s into %s." % (global_step_value, filename))
		pylab.savefig(filename, dip=100)

class EpochLoggingTensorHook(tf.train.SessionRunHook):
	def __init__(self, epoch_num, global_step_op, gen_loss, dis_loss):
		"""
		:epoch_num: iteratorに対するepochの数(epoch_num=10: 10 iter == 1 epoch)
		"""
		self._tensors = {"step": global_step_op,
						 "gen_loss": gen_loss,
						 "dis_loss": dis_loss}
		self._tag_order = self._tensors.keys()
		self._epoch_num = epoch_num

	def begin(self):
		self._iter_count = 0
		self._epoch_count = 0
		self._current_tensors = {tag: _as_graph_element(tensor)
								 for (tag, tensor) in self._tensors.items()}
		self._gen_loss_sum = np.float32(0)
		self._dis_loss_sum = np.float32(0)

	def before_run(self, run_context):
		return tf.train.SessionRunArgs(self._current_tensors)

	def after_run(self, run_context, run_values):
		_ = run_context
		step = run_values.results["step"]
		gen_loss = run_values.results["gen_loss"]
		dis_loss = run_values.results["dis_loss"]
		self._gen_loss_sum += gen_loss
		self._dis_loss_sum += dis_loss

		if self._iter_count != 0 and self._iter_count % self._epoch_num == 0:
			log_format = "Epoch %4d: gen_loss=%6.8f, dis_loss=%6.8f"
			tf.logging.info(log_format % (self._epoch_count, self._gen_loss_sum, self._dis_loss_sum))
			self._epoch_count += 1
			self._gen_loss_sum = np.float32(0)
			self._dis_loss_sum = np.float32(0)
		else:
			log_format = "Iter %4d: gen_loss=%6.8f, dis_loss=%6.8f\r"
			# logging感出す
			sys.stdout.write("INFO:tensorflow:" + log_format % (step, gen_loss, dis_loss))
			sys.stdout.flush()
			time.sleep(0.01)
		self._iter_count += 1
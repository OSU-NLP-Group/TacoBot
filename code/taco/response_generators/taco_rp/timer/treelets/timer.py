import time

class TimerManagement(object):

    def __init__(self):
        self.id2time = {}
        self.id2pause = {}
        pass

    def create_timer(self, duration, timer_label):
        """
        Create a new timer.
        :param create_timer_request: (required)
        :type create_timer_request: ask_sdk_model.services.timer_management.timer_request.TimerRequest
        :rtype: TimerResponse
        """
        start_time = time.time()
        self.id2time[timer_label] = [start_time, duration]
        response = {}
        response['timer_label'] = timer_label
        return response

    def pause_timer(self, timer_id: str):
        """
        This API pauses a timer

        :param timer_id: (required)
        :type timer_id: str
        """
        try:
            self.id2pause[timer_id] = time.time()
            self.logger.info(f"Timer with ID {timer_id} paused successfully.")
        except Exception as err:
            self.logger.error(f"Error pausing timer with ID {timer_id} - {err}")
            raise

    def cancel_timer(self, timer_id: str):
        """
        This API deletes a timer

        :param timer_id: (required)
        :type timer_id: str
        """
        try:
            del self.id2time[timer_id]
            if timer_id in self.id2pause:
                self.id2pause[timer_id]

            self.logger.error(f"Timer with ID {timer_id} was deleted successfully.")
        except Exception as err:
            self.logger.error(f"Error deleting timer with ID {timer_id} - {err}")
            raise

    def cancel_all_timers(self):
        """
        This API deletes all timers
        """
        try:
            self.id2time = {}
            self.id2pause = {}
            self.logger.info("Deleted all timers!")
        except Exception as err:
            self.logger.error(err)
            raise

    def resume_timer(self, timer_id: str):
        """
        This API resumes a timer

        :param timer_id: (required)
        :type timer_id: str
        """
        try:
            timer_set = self.id2time[timer_id]
            pause_st =  self.id2pause[timer_id]
            if timer_id in self.id2pause:
                self.id2pause[timer_id]
            start_time = time.time()
            self.id2time['timer_id'] = [start_time, duration - pause_st + timer_set]
            self.logger.info(f"Timer with ID {timer_id} was resumed successfully.")
        except Exception as err:
            self.logger.error(f"Error resuming timer with ID {timer_id} - {err}")
            raise

    def read_timer(self, timer_id: str):
        """
        Retrieves a timer set by the user given timer_id

        :param timer_id: (required) timer to resume
        :type timer_id: str
        :rtype: TimerResponse
        """
        try:
            timer_st = self.id2time['timer_id']
            if timer_id in self.id2pause:
                timer_remain = self.id2pause[timer_id] - timer_st
            else:
                timer_remain =  time.time() - timer_st
            response = {}
            response['timer_label'] = timer_id
        except Exception as err:
            self.logger.error(f"Unable to get timer with ID {timer_id} - {err}")
            raise
        else:
            return response

    def read_all_timers(self):
        """
        Retrieves all the timers set by the user

        :rtype: TimersResponse
        """
        total_count = len(self.id2time)
        timers = self.id2time.keys()
        response = {}
        response['timers'] = timers
        response['total_count'] = total_count
        return response


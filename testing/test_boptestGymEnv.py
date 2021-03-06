'''
Module to test features of the OpenAI-Gym interface for BOPTEST. 
The BOPTEST bestest_hydronic_heat_pump case needs to be deployed to perform
the tests. 

'''

import unittest
import utilities
import os
import pandas as pd
import random
import shutil
from examples import run_baseline, run_sample, run_save_callback,\
    run_variable_episode, train_A2C, train_PPO2
from collections import OrderedDict
from boptestGymEnv import BoptestGymEnv
from stable_baselines.common.env_checker import check_env
from stable_baselines import A2C

url = 'http://127.0.0.1:5000'

class BoptestGymEnvTest(unittest.TestCase, utilities.partialChecks):
    '''Tests the OpenAI-Gym interface for BOPTESTS.
         
    '''
 
    def setUp(self):
        '''Setup for each test.
         
        '''
        self.env = BoptestGymEnv(url                 = url,
                                actions             = ['oveHeaPumY_u'],
                                observations        = {'reaTZon_y':(280.,310.)}, 
                                reward              = ['reward'],
                                max_episode_length  = 24*3600,
                                random_start_time   = True,
                                warmup_period       = 3600,
                                step_period         = 900)
    
    def test_summary(self):
        '''
        Test that the environment can print, save, and load a summary 
        describing its most important attributes.  
        
        '''
        
        # Check that we can print the environment summary
        print(self.env)
        
        # Check that we can save the environment summary
        file_ref = os.path.join('references','summary_ref')
        file_tst = 'summary_tst'
        self.env.save_summary(file_tst)
        
        # Check that we can load the environment summary. This test only checks sorted keys
        summary = self.env.load_summary(file_tst)
        for i,k in enumerate(summary.keys()):
            self.compare_ref_json(sorted(dict(summary[k])), file_ref+'_'+str(i)+'.json')
        
        # Remove generated file
        os.remove(file_tst+'.json')

    def test_stable_baselines_check(self):
        '''Use the environment checker from stable baselines to test 
        the environment. This checks that the environment follows the 
        Gym API. It also optionally checks that the environment is 
        compatible with Stable-Baselines repository.
        
        '''
        
        check_env(self.env, warn=True)
   
    def test_reset_fixed(self):
        '''Test that the environment can reset using a fixed start time
        and a specific warmup period. 
        
        '''
        
        self.env.random_start_time  = False
        self.env.start_time         = 14*24*3600
        self.env.warmup_period      = 3*3600
        
        obs = self.env.reset()
        
        # Check values
        df = pd.DataFrame(data=[obs], index=['obs_reset_fixed'], columns=['value'])
        df.index.name = 'keys'
        ref_filepath = os.path.join(utilities.get_root_path(), 'testing', 'references', 'reset_fixed.csv')
        self.compare_ref_values_df(df, ref_filepath)

    def test_reset_random(self):
        '''Test that the environment can reset using a random start time
        that is out of the specified `excluding_periods`. This test also
        checks that the seed for random initialization works properly. 
        
        '''
        
        self.env.random_start_time  = True
        self.env.warmup_period      = 1*3600
        # Set the excluding periods to be the two first weeks of February
        # and the two first weeks of November
        excluding_periods = [(31*24*3600,  31*24*3600+14*24*3600),
                            (304*24*3600, 304*24*3600+14*24*3600)]
        self.env.excluding_periods = excluding_periods
        random.seed(123456)
        start_times = OrderedDict()
        # Reset hundred times
        for i in range(100):
            obs = self.env.reset()
            start_time = self.env.start_time
            episode = (start_time, start_time+self.env.max_episode_length)
            for period in excluding_periods:
                # Make sure that the episodes don't overlap with excluding_periods
                assert not(episode[0] < period[1] and period[0] < episode[1]),\
                        'reset is not working properly when generating random times. '\
                        'The episode with starting time {0} and end time {1} '\
                        'overlaps with period {2}. This corresponds to the '\
                        'generated starting time number {3}.'\
                        ''.format(start_time,start_time+self.env.max_episode_length,period,i)
            start_times[start_time] = obs
            
        # Check values
        df = pd.DataFrame.from_dict(start_times, orient = 'index', columns=['value'])
        df.index.name = 'keys'
        ref_filepath = os.path.join(utilities.get_root_path(), 'testing', 'references', 'reset_random.csv')
        self.compare_ref_values_df(df, ref_filepath) 

    def test_compute_reward_default(self):
        '''Test default method to compute reward.
        
        '''
        obs, _, rew = run_baseline.run_reward_default(plot=False)
        self.check_obs_act_rew_kpi(obs=obs,act=None,rew=rew,kpi=None,label='default')

    def test_compute_reward_custom(self):
        '''Test custom method to compute reward.
        
        '''
        obs, _, rew = run_baseline.run_reward_custom(plot=False)
        self.check_obs_act_rew_kpi(obs=obs,act=None,rew=rew,kpi=None,label='custom')
        
    def test_compute_reward_clipping(self):
        '''Test reward clipping.
        
        '''
        obs, _, rew = run_baseline.run_reward_clipping(plot=False)
        self.check_obs_act_rew_kpi(obs=obs,act=None,rew=rew,kpi=None,label='clipping')

    def test_normalized_observation_wrapper(self):
        '''Test wrapper that normalizes observations.
        
        '''
        obs, _, rew = run_baseline.run_normalized_observation_wrapper(plot=False)
        self.check_obs_act_rew_kpi(obs=obs,act=None,rew=rew,kpi=None,label='normalizedObservationWrapper')
        
    def test_normalized_action_wrapper(self):
        '''Test wrapper that normalizes actions.
        
        '''
        obs, act, rew = run_sample.run_normalized_action_wrapper(plot=False)
        self.check_obs_act_rew_kpi(obs=obs,act=act,rew=rew,kpi=None,label='normalizedActionWrapper')
    
    def test_set_scenario(self):
        '''Test that environment can set BOPTEST case scenario.
        
        '''
        obs, _, rew = run_baseline.run_highly_dynamic_price(plot=False)
        self.check_obs_act_rew_kpi(obs=obs,act=None,rew=rew,kpi=None,label='setScenario')
    
    def partial_test_A2C(self, load=True, episode_length_test=1*24*3600,
                 warmup_period_test=1*24*3600, case='simple', plot=False):
        '''Test for an A2C agent from stable baselines. 
        
        Parameters
        ----------
        load : boolean, default=True
            If `load=False`, then this test case will be a long test run 
            since the agent will be trained during the tests. Setting 
            `load=True` reduces the testing time considerably by directly 
            loading a pre-trained agent. Independently of whether the 
            agent is trained or not during testing, the results should be 
            exactly the same as far as the seed in `examples.train_A2C` 
            is not modified. 
        episode_length_test : integer, default=2*24*3600
            Length of the testing episode. We keep it short for testing,
            only one day is used by default. 
        warmup_period_test : integer, default=1*24*3600
            Length of the initialization period for the test. We keep it 
            short for testing. Only one day is used by default. 
        
        '''        
        
        env, model, start_time_tests = train_A2C.train_A2C(load=load, 
                                                           case=case,
                                                           tensorboard_log=None)
        
        obs, act, rew, kpi = \
            train_A2C.test_feb(env, model, start_time_tests, 
                               episode_length_test, warmup_period_test, plot)
        self.check_obs_act_rew_kpi(obs,act,rew,kpi,label='A2C_{}_feb'.format(case))
        
        obs, act, rew, kpi = \
            train_A2C.test_nov(env, model, start_time_tests, 
                               episode_length_test, warmup_period_test, plot)
        self.check_obs_act_rew_kpi(obs,act,rew,kpi,label='A2C_{}_nov'.format(case))
    
    def test_A2C_simple(self):
        '''Test simple agent with only one measurement as observation and
        one action. The agent has been trained with 1e5 steps. 
        
        '''
        
        # Use two days in this simple test. All others use only one. 
        self.partial_test_A2C(case='simple', episode_length_test=2*24*3600)
        
    def test_A2C_A(self):
        '''Test case A which extends simple case with `time` as observation
        and sets the highly_dynamic price scenario. Hence, this test
        checks the inclusion of time and boundary condition data in the 
        state space. 
        
        '''
        self.partial_test_A2C(case='A')
        
    def test_A2C_B(self):
        '''Test case B which extends case A with boundary condition data 
        in the state. Specifically it includes the comfort bounds in the 
        state. Hence, this test checks the inclusion of boundary condition
        data in the state space. 
        
        '''
        self.partial_test_A2C(case='B')
        
    def test_A2C_C(self):
        '''Test case C which extends case B with boundary forecast. 
        Specifically it uses a 3 hours forecasting period. Hence, this 
        test checks the use of predictive states. 
        
        '''
        self.partial_test_A2C(case='C')
       
    def test_PPO2(self, load=True, episode_length_test=2*24*3600,
                 warmup_period_test=1*24*3600, plot=False):
        '''Test for an PPO2 agent from stable baselines. 
        
        Parameters
        ----------
        load : boolean, default=True
            If `load=False`, then this test case will be a long test run 
            since the agent will be trained during the tests. Setting 
            `load=True` reduces the testing time considerably by directly 
            loading a pre-trained agent. Independently of whether the 
            agent is trained or not during testing, the results should be 
            exactly the same as far as the seed in `examples.train_PPO2` 
            is not modified. 
        episode_length_test : integer, default=2*24*3600
            Length of the testing episode. We keep it short for testing,
            only two days are used by default. 
        warmup_period_test : integer, default=1*24*3600
            Length of the initialization period for the test. We keep it 
            short for testing. Only one day is used by default. 
        
        '''        
        
        env, model, start_time_tests = train_PPO2.train_PPO2(load=load, 
                                                             tensorboard_log=None)
        
        obs, act, rew, kpi = \
            train_PPO2.test_feb(env, model, start_time_tests, 
                               episode_length_test, warmup_period_test, plot)
        self.check_obs_act_rew_kpi(obs,act,rew,kpi,label='PPO2_feb')
        
        obs, act, rew, kpi = \
            train_PPO2.test_nov(env, model, start_time_tests, 
                               episode_length_test, warmup_period_test, plot)
        self.check_obs_act_rew_kpi(obs,act,rew,kpi,label='PPO2_nov')

    def test_save_callback(self):
        '''
        Test that the model performance can be monitored and results can be 
        checked and saved as the model improves. This test trains an agent
        for a short period of time, without loading a pre-trained model. 
        Therefore, this test also checks that a RL from stable-baselines 
        can be trained.
        
        '''
        # Define logging directory. Monitoring data and agent model will be stored here
        log_dir = os.path.join(utilities.get_root_path(), 'examples', 'agents', 
                               'monitored_A2C')
        
        # Perform a short training example with callback
        env, _, _ = run_save_callback.train_A2C_with_callback(log_dir=log_dir,
                                                              tensorboard_log=None)  
        
        # Load the trained agent
        model = A2C.load(os.path.join(log_dir, 'best_model'))
        
        # Test one step with the trained model
        obs = env.reset()
        df = pd.DataFrame([model.predict(obs)[0][0]], columns=['value'])
        df.index.name = 'keys'
        ref_filepath    = os.path.join(utilities.get_root_path(), 
                            'testing', 'references', 'save_callback.csv')
        self.compare_ref_values_df(df, ref_filepath)
        
        # Remove model to prove further testing
        shutil.rmtree(log_dir, ignore_errors=True)
        
    def test_variable_episode(self):
        '''
        Test that a model can be trained using variable episode length. 
        The method that is used to determine whether the episode is 
        terminated or not is defined by the user. This test trains an agent
        for a short period of time, without loading a pre-trained model. 
        Therefore, this test also checks that a RL from stable-baselines 
        can be trained. This test also uses the save callback to check that
        the variable episode length is being effectively used. 
        Notice that this test also checks that child classes can be nested
        since the example redefines the `compute_reward` and the 
        `compute_done` methods. 
        
        '''
        # Define logging directory. Monitoring data and agent model will be stored here
        log_dir = os.path.join(utilities.get_root_path(), 'examples', 'agents', 
                               'variable_episode_A2C')
        
        # Perform a short training example with callback
        env, _, _ = run_variable_episode.train_A2C_with_variable_episode(log_dir=log_dir,
                                                                         tensorboard_log=None)  
        
        # Load the trained agent
        model = A2C.load(os.path.join(log_dir, 'best_model'))
        
        # Test one step with the trained model
        obs = env.reset()
        df = pd.DataFrame([model.predict(obs)[0][0]], columns=['value'])
        df.index.name = 'keys'
        ref_filepath    = os.path.join(utilities.get_root_path(), 
                            'testing', 'references', 'variable_episode_step.csv')
        self.compare_ref_values_df(df, ref_filepath)
        
        # Check variable lengths
        monitor = pd.read_csv(os.path.join(log_dir,'monitor.csv'),index_col=None)
        monitor = monitor.iloc[1:]
        monitor.reset_index(inplace=True)
        monitor.columns =['reward','episode_length','time']
        
        # Time may vary from one computer to another
        monitor.drop(labels='time',axis=1,inplace=True)
        
        # Utilities require index to have time as index name (even this is not the case here)
        monitor.index.name = 'time'
        
        # Transfor to numeric
        monitor = monitor.apply(lambda col:pd.to_numeric(col, errors='coerce'))
        
        # Check that we obtain always same monitoring parameters
        ref_filepath = os.path.join(utilities.get_root_path(), 
                    'testing', 'references', 'variable_episode_monitor.csv')
        self.compare_ref_timeseries_df(monitor, ref_filepath)
        
        # Remove model to prove further testing
        shutil.rmtree(log_dir, ignore_errors=True)
        
    def check_obs_act_rew_kpi(self, obs=None, act=None, rew=None, kpi=None,
                              label='default'):
        '''Auxiliary method to check for observations, actions, rewards, 
        and/or kpis of a particular test case run. 
        
        '''
        
        # Check observation values
        if obs is not None:
            df = pd.DataFrame(obs)
            df.index.name = 'time'
            ref_filepath = os.path.join(utilities.get_root_path(), 'testing', 'references', 'observations_{}.csv'.format(label))
            self.compare_ref_timeseries_df(df, ref_filepath) 
        
        # Check actions values
        if act is not None:
            df = pd.DataFrame(act)
            df.index.name = 'time'
            ref_filepath = os.path.join(utilities.get_root_path(), 'testing', 'references', 'actions_{}.csv'.format(label))
            self.compare_ref_timeseries_df(df, ref_filepath) 
        
        # Check reward values
        if rew is not None:
            df = pd.DataFrame(rew)
            df.index.name = 'time'
            ref_filepath = os.path.join(utilities.get_root_path(), 'testing', 'references', 'rewards_{}.csv'.format(label))
            self.compare_ref_timeseries_df(df, ref_filepath) 
            
        if kpi is not None:
            df = pd.DataFrame(data=[kpi]).T
            df.columns = ['value']
            df.index.name = 'keys'
            # Time ratio is not checked since depends on the machine where tests are run
            df.drop('time_rat', inplace=True) 
            ref_filepath = os.path.join(utilities.get_root_path(), 'testing', 'references', 'kpis_{}.csv'.format(label))
            self.compare_ref_values_df(df, ref_filepath)
        
if __name__ == '__main__':
    utilities.run_tests(os.path.basename(__file__))

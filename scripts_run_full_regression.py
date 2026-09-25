import gc, unittest, warnings, sys, time
class GCResult(unittest.TextTestResult):
    def stopTest(self, test):
        super().stopTest(test)
        gc.collect()

def main():
    warnings.simplefilter('error', ResourceWarning)
    suite=unittest.defaultTestLoader.discover('tests', pattern='test*.py')
    runner=unittest.TextTestRunner(verbosity=1,resultclass=GCResult)
    t=time.time(); result=runner.run(suite)
    print(f'FULL_REGRESSION_SECONDS={time.time()-t:.2f}')
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__': sys.exit(main())

# coding:utf8

'''
MySQL数据库性能诊断
'''

from collections import OrderedDict
import sys
reload(sys)
sys.setdefaultencoding('utf8')


class Get_mysql_tuning():
    def __init__(self):
        pass

    def human(self,bytes):
        bytes = float(bytes)
        if bytes >= 1099511627776:
            terabytes = bytes / 1099511627776
            size = '%.0fT' % terabytes
        elif bytes >= 1073741824:
            gigabytes = bytes / 1073741824
            size = '%.0fG' % gigabytes
        elif bytes >= 1048576:
            megabytes = bytes / 1048576
            size = '%.0fM' % megabytes
        elif bytes >= 1024:
            kilobytes = bytes / 1024
            size = '%.0fK' % kilobytes
        else:
            size = '%.0fb' % bytes
        return size


    def print_check(self, **kwargs):
        """
        返回数据库检查项目
        :param Issue: 检查的内容
        :param Category: 分类
        :param Descreption: 描述
        :param Reference: 帮助链接
        :param Solution: 解决建议
        :param result: 检查项种涉及到的变量和状态值
        :return: 返回有序字典OrderedDict
        """
        a = OrderedDict()
        if 'result' in kwargs:
            result = kwargs['result']
            for k,v in result.iteritems():
                        a[k] = v
        if 'Issue' in kwargs:
            a['Issue'] = kwargs['Issue']

        if 'Category' in kwargs:
            a['Category'] = kwargs['Category']

        if 'Description' in kwargs:
            a['Description'] = kwargs['Description']

        if 'Reference' in kwargs:
            a['Reference'] = kwargs['Reference']

        if 'Solution' in kwargs:
            a['Solution'] = kwargs['Solution']

        return a

    def get_mysql_variables(self):
        """
        获取数据库中所有的变量值，后续check时会用到
        :return: 字典
        """
        self.myv = {}
        for line in open('mysql_global_variables.sql').readlines():
            line_list= line.strip().split('\t')
            if len(line_list) == 1:
                key = line_list[0]
                value = None
            else:
                key,value = line_list
            self.myv[key] = value
        return self.myv

    def get_mysql_status(self):
        """
        获取数据库当前所有的状态值，后续check时会用到
        :return: 字典
        """
        self.mys = {}
        for line in open('mysql_global_status.sql').readlines():
            key,value = line.strip().split('\t')
            self.mys[key] = value
        return self.mys

    def status_report(self):
        """
        数据库基本信息
        :return: string
        """

        uptime = self.mys['Uptime']
        questions = self.mys['Questions']
        threads = self.mys['Threads_connected']
        avg_qps = float(questions)/float(uptime)

        return "QPS平均负载 : {0:.2f}\n查询统计 : {1}\n已连接的会话数 : {2}\n".format(avg_qps,questions,threads)



    def check_ratio_aborterd_connections(self):
        """
        检查失败连接的比率
        :return: OrderedDict
        """
        Category = "检查失败连接的比率"

        Aborted_connects = int(self.mys['Aborted_connects'])
        Connections = int(self.mys['Connections'])
        Aborted_connects_ratio = round((float(Aborted_connects) / Connections),2)

        result = OrderedDict()
        result['Total connections'] = Connections
        result['Total aborted connections'] = Aborted_connects
        result['Percentage , Aborted connections ratio'] = Aborted_connects_ratio

        if Aborted_connects_ratio > 0.1:
            Issue = "存在大量失败连接"
            Description = "存在超过10%的失败连接，这个警报发现了大量与数据库的中断连接。"
            Reference = "http://dev.mysql.com/doc/refman/5.7/en/server-system-variables.html#option_mysqld_wait_timeout"
            Solution = "造成这种情况的一个常见原因是，由于连接超时到达，应用程序或锁定的表之间的连接被不正确地关闭，导致随后的连接中断。这个警告建议审核您的代码，以便正确关闭连接，或者在一个临时环境中测试正在测试的查询，以监视锁定的表。"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                                    Solution=Solution, result=result)
        else:
            Issue = "失败连接比率正常"
            return self.print_check(Issue=Issue, Category=Category)

    def check_ratio_max_connections(self):
        """
        检查最大连接数占比
        :return: OrderedDict
        """
        Category = "检查最大连接数占比"
        max_connections = int(self.myv['max_connections'])
        Threads_connected = int(self.mys['Threads_connected'])
        Max_used_connections = int(self.mys['Max_used_connections'])
        connections_ratio = round((float(Max_used_connections) / max_connections), 2)
        max_connect_R = round((Max_used_connections * 1.25),2)

        result = OrderedDict()
        result['Current max_connections'] = max_connections
        result['Current Threads_connected'] = Threads_connected
        result['Historic Max_used_connections'] = Max_used_connections
        result['Percentagte, The number of used connections is'] = connections_ratio

        if connections_ratio > 0.85:
            Issue = "最大连接数配置有问题。(max_connections = {0})".format(max_connect_R)
            Description = "服务器连接配置需要进行优化"
            Reference = "http://dev.mysql.com/doc/refman/5.7/en/too-many-connections.html "
            Solution = "更改max_connections的值，以实现85%的最大利用率。请记住，增加连接数量将增加每个线程缓冲区使用的RAM的数量。"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                                    Solution=Solution, result=result)
        else:
            Issue = '最大连接数配置正常'
            return self.print_check(Issue=Issue, Category=Category, result=result)

    def check_slowlog(self):
        """
        检查慢查询
        :return:
        """
        Category = "检查慢查询"
        long_query_time = self.myv['long_query_time']
        slow_query_log = self.myv['slow_query_log']
        slow_query_log_file = self.myv['slow_query_log_file']
        min_examined_row_limit = self.myv['min_examined_row_limit']
        log_queries_not_using_indexes = self.myv['log_queries_not_using_indexes']
        slow_queries = int(self.mys['Slow_queries'])
        questions = int(self.mys['Questions'])
        slow_query_ratio = round((float(slow_queries) / questions),2)

        result = OrderedDict()
        result['long_query_time'] = long_query_time
        result['slow_query_log'] = slow_query_log
        result['slow_query_log_file'] = slow_query_log_file
        result['min_examined_row_limit'] = min_examined_row_limit
        result['log_queries_not_using_indexes'] = log_queries_not_using_indexes
        result['slow_queries'] = slow_queries
        result['slow_query_ratio'] = slow_query_ratio


        if slow_query_log == 'ON':

            if slow_query_ratio > 0.1 :
                Issue = '慢查询占比较高'
                Description = "慢查询较多需要优化"
                Reference = "https://dev.mysql.com/doc/refman/5.7/en/server-status-variables.html#statvar_Slow_queries "
                Solution = "根据您的工作角色(开发人员、DBA或两者的组合)，您可以优化单个SQL语句、整个应用程序、单个数据库服务器或多个网络数据库服务器的级别。有时您可以提前计划并提前计划性能，而其他时候您可能会在出现问题之后对配置或代码问题进行故障排除。优化CPU和内存使用情况还可以提高可伸缩性,允许数据库来处理更多的负载没有放缓down.https:/ /dev.mysql.com/doc/refman/5.7/en/optimization.html"
                return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                                        Solution=Solution, result=result)
            else:
                Issue = '慢查询占比不高'
                return self.print_check(Issue=Issue, Category=Category,result=result)
        else:
            Issue = '没有开启慢查询'
            Description = "慢查询日志需要开启"
            Reference = "https://dev.mysql.com/doc/refman/5.7/en/server-status-variables.html#statvar_Slow_queries "
            Solution = "通过在mysql配置文件中添加配置 slow_query_log = ON 来启用慢查询日志。"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                                    Solution=Solution, result=result)

    def check_binlog(self):
        """
        检查binlog
        :return: OrderedDict
        """
        Category = "检查二进制日志"
        log_bin = self.myv['log_bin']
        binlog_format = self.myv['binlog_format']
        sync_binlog = self.myv['sync_binlog']
        expire_logs_days = self.myv['expire_logs_days']
        result = OrderedDict()
        result['log_bin'] = log_bin
        result['binlog_format'] = binlog_format
        result['sync_binlog'] = sync_binlog
        result['expire_logs_days'] = expire_logs_days

        if log_bin == 'ON':
            Issue_list= []
            if binlog_format != 'ROW':
                Issue_list.append('二进制日志格式为ROW；')
            elif int(sync_binlog) != 1:
                Issue_list.append('sync binlog值不是 1；')
            elif int(expire_logs_days) == 0:
                Issue_list.append('二进制日志自动清理阈值expire_log_days应该大于0')
            Issue = ' '.join(Issue_list)
            Description = "二进制日志格式应该设为ROW ；二进制日志建议在每次写入时被同步到磁盘上； 二进制日志自动清理阈值expire_log_days应该大于0 "
            Reference = "http://dev.mysql.com/doc/refman/5.7/en/binary-log.html"
            Solution = "您需要修改配置文件，添加或修改二进制日志的相关参数。"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                                    Solution=Solution, result=result)
        else:
            Issue_list = ['二进制日志没有开启；']
            if binlog_format != 'ROW':
                Issue_list.append('二进制日志格式为ROW；')
            elif int(sync_binlog) != 1:
                Issue_list.append('sync binlog值不是 1；')
            elif int(expire_logs_days) == 0:
                Issue_list.append('二进制日志自动清理阈值expire_log_days应该大于0')
            Issue = ' '.join(Issue_list)
            Description = "二进制日志需要开启；二进制日志格式应该设为ROW ；二进制日志建议在每次写入时被同步到磁盘上； 二进制日志自动清理阈值expire_log_days应该大于0 "
            Reference = "http://dev.mysql.com/doc/refman/5.7/en/binary-log.html"
            Solution = "您需要修改配置文件，添加或修改二进制日志的相关参数。"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                                    Solution=Solution, result=result)

    def check_innodb(self):
        """
        检查innodb存储引擎的情况
        :return: OrderedDict
        """
        Category = '检查innodb存储引擎的情况'

        innodb_flush_log_at_trx_commit = self.myv['innodb_flush_log_at_trx_commit']
        innodb_doublewrite = self.myv['innodb_doublewrite']
        tx_isolation = self.myv['tx_isolation']
        innodb_lock_wait_timeout =self.myv['innodb_lock_wait_timeout']  #

        result = OrderedDict()
        result['innodb_flush_log_at_trx_commit'] = innodb_flush_log_at_trx_commit
        result['innodb_doublewrite'] = innodb_doublewrite
        result['tx_isolation'] = tx_isolation
        result['innodb_lock_wait_timeout'] = innodb_lock_wait_timeout

        if int(innodb_flush_log_at_trx_commit) == 1 and innodb_doublewrite == 'ON':
            Issue = 'innodb配置良好'
        else:
            Issue = '请检查innodb的相关配置'
        return self.print_check( Issue=Issue,Category=Category,result=result)

    def check_table_scans(self):
        """
        检查临时表使用情况
        :return: OrderedDict
        """
        Category = '检查临时表使用情况'

        max_heap_table_size = self.myv['max_heap_table_size']
        tmp_table_size = self.myv['tmp_table_size']
        real_tmp_table_size = min(max_heap_table_size,tmp_table_size)

        Created_tmp_disk_tables = self.mys['Created_tmp_disk_tables']
        Created_tmp_files = self.mys['Created_tmp_files']
        Created_tmp_tables = self.mys['Created_tmp_tables']
        tmp_table_raito = '{0:.1}'.format(float(Created_tmp_disk_tables) / float(Created_tmp_tables))

        result = OrderedDict()
        result['real_tmp_table_size'] = real_tmp_table_size
        result['Created_tmp_disk_tables'] = Created_tmp_disk_tables
        result['Created_tmp_files'] = Created_tmp_files
        result['Created_tmp_tables'] = Created_tmp_tables
        result['tmp_table_raito'] = tmp_table_raito

        if tmp_table_raito <= 0.25:
            Issue = '临时表使用情况良好'
            return self.print_check(Issue=Issue, Category=Category, result=result)
        else:
            Issue = '临时表配置需要优化'
            Description = "比较理想的配置是：Created_tmp_disk_tables / Created_tmp_tables * 100% <= 25%。"
            Reference = "https://dev.mysql.com/doc/refman/5.7/en/server-status-variables.html#statvar_Created_tmp_disk_tables"
            Solution = "在优化查询语句时，避免使用临时表，如果无法避免，请确保这些临时表在内存中。"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                                    Solution=Solution, result=result)

    def check_open_table(self):
        """
        检查open table的情况
        :return:
        """
        Category = '检查open table的情况'
        table_open_cache = self.myv['table_open_cache']
        Open_tables = self.mys['Open_tables']
        Opened_tables = self.mys['Opened_tables']
        table_cache_hit_rate = float(Open_tables) / float(Opened_tables)
        table_cache_fill = float(Open_tables) / float(table_open_cache)

        result = OrderedDict()
        result['table_open_cache'] = table_open_cache
        result['Open_tables'] = Open_tables
        result['Opened_tables'] = Opened_tables
        result['table_cache_hit_rate'] = '{0:.1}'.format(table_cache_hit_rate)
        result['table_cache_fill'] = '{0:.1}'.format(table_cache_fill)

        if table_cache_fill < 0.95:
            Issue = '表缓存配置正常'
            return self.print_check(Issue=Issue, Category=Category, result=result)
        elif table_cache_hit_rate <= 0.85:
            Issue = '表缓存配置不正常'
            Reference = "https://dev.mysql.com/doc/refman/5.7/en/server-status-variables.html#table__open_cache"
            Description = "打开表的数量/打开过的表数量 应该大于等于0.95 ，打开表的数量/表缓存 应该小于等于 0.85"
            Solution = "您可能需要提高table_open_cache配置。"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                                    Solution=Solution, result=result)
        else:
            Issue = '表缓存配置正常'
            return self.print_check(Issue=Issue, Category=Category, result=result)

    def check_threads(self):
        """
        检查线程缓冲
        :return: OrderedDict
        """
        Category = '检查线程缓冲'
        thread_cache_size = self.myv['thread_cache_size']
        Threads_created1 = self.mys['Threads_created']
        Threads_created2 = self.mys['Threads_created']
        Threads_cached = self.mys['Threads_cached']
        Uptime = self.mys['Uptime']
        historic_threads_per_sec = round((float(Threads_created1) / int(Uptime)),4)
        current_threads_per_sec = round((float(Threads_created2) - int(Threads_created1)),4)
        result = OrderedDict()
        result['thread_cache_size'] = thread_cache_size
        result['Threads_created'] = Threads_created1
        result['Threads_cached'] = Threads_cached
        result['historic_threads_per_sec'] = historic_threads_per_sec
        result['current_threads_per_sec'] = current_threads_per_sec

        if ( historic_threads_per_sec >= 2 or current_threads_per_sec >= 2 ) and Threads_cached <= 1:
            Issue = "线程缓存数thread_cache_size配置不合理"
            Reference = "https://dev.mysql.com/doc/refman/5.7/en/server-status-variables.html#thread_cache_size"
            Description = "您应该提高thread_cache_size。"
            Solution = "您应该增加thread_cache_size。默认值基于以下公式，上限为100:[8 + (max_connections / 100)]。"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                                    Solution=Solution, result=result)
        else:
            Issue = "线程缓存数thread_cache_size配置正常"
            return self.print_check(Issue=Issue, Category=Category, result=result)

    def check_query_cache_type(self):
        """
        检查查询缓存是否关闭
        :return: OrderedDict
        """
        Category = '检查查询缓存是否关闭'
        query_cache_type = self.myv['query_cache_type']
        result = OrderedDict()
        result['query_cache_type'] = query_cache_type
        if query_cache_type == 'OFF':
            Issue = '查询缓冲已关闭'
            return self.print_check(Issue=Issue, Category=Category, result=result)
        else:
            Issue = '查询缓冲仍然开启'
            Description = '关闭查询缓冲后不会缓存结果或从查询缓存中检索结果。'
            Reference = 'http://dev.mysql.com/doc/refman/5.7/en/server-system-variables.html#option_mysqld_query_cache_size'
            Solution = "您目前还没有释放查询缓存缓冲区，您应该将query_cache_size设置为0。"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                                Solution=Solution, result=result)

    def check_sort_buffer(self):
        """
        检查排序缓冲
        :return: OrderedDict
        """
        Category = '检查排序缓冲'
        sort_buffer_size = self.myv['sort_buffer_size']
        read_rnd_buffer_size = self.myv['read_rnd_buffer_size']
        Sort_merge_passes = self.mys['Sort_merge_passes']
        Sort_scan = self.mys['Sort_scan']
        Sort_range = self.mys['Sort_range']
        total_sorts = int(Sort_scan) + int(Sort_range)
        passes_per_sort = round((float(Sort_merge_passes) / int(total_sorts)),4)

        result = OrderedDict()
        result['sort_buffer_size'] = self.human(sort_buffer_size)
        result['read_rnd_buffer_size'] = self.human(read_rnd_buffer_size)
        result['Sort_merge_passes'] = Sort_merge_passes
        result['Sort_scan'] = Sort_scan
        result['Sort_range'] = Sort_range
        result['total_sorts'] = total_sorts
        result['passes_per_sort'] = passes_per_sort

        if passes_per_sort >= 2:
            Issue = "排序缓存配置不合理"
            Reference = "https://dev.mysql.com/doc/refman/5.7/en/server-status-variables.html#sort_buffer_size"
            Description = "排序缓冲区的分配比所需的值更大。"
            Solution = "您应该提高sort_buffer_size，还应该提高read_rnd_buffer_size。"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                                    Solution=Solution, result=result)
        else:
            Issue = "排序缓存配置正常"
            return self.print_check(Issue=Issue, Category=Category, result=result)

    def check_join_buffer_size(self):
        """
        检查join缓存使用情况
        :return: 
        """
        Category = '检查join缓存使用情况'
        Select_full_join = self.mys['Select_full_join']
        Select_range_check = self.mys['Select_range_check']
        join_buffer_size = self.myv['join_buffer_size']
        join_buffer_size = int(join_buffer_size) + 4096

        result = OrderedDict()
        result['Select_full_join'] = Select_full_join
        result['Select_range_check'] = Select_range_check
        result['join_buffer_size'] = self.human(join_buffer_size)

        if Select_range_check == '0' and  Select_full_join == '0':
            Issue = "您的连接似乎正确地使用了索引。"
            return self.print_check(Issue=Issue, Category=Category, result=result)
        else:
            Issue = "您的连接似乎没有正确地使用索引。"
            Reference = "https://dev.mysql.com/doc/refman/5.7/en/server-status-variables.html#sort_buffer_size"
            Description = "您已经有{0}个join，没有使用索引导致需要全表扫描。".format(Select_range_check)
            Solution = "您可以开启log-queries-not-using-indexes参数，然后在慢速查询日志中查找非索引join语句。如果您无法优化您的查询，您可能希望增加您的join_buffer_size，以容纳更大的连接。"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                            Solution=Solution, result=result)

    def check_open_files_limit(self):
        """
        检查打开的文件数情况
        :return:
        """
        Category = '检查打开的文件数情况'
        open_files_limit = self.myv['open_files_limit']
        Open_files = self.mys['Open_files']
        open_files_ratio = round((int(Open_files)  / float(open_files_limit)),4)
        result = OrderedDict()
        result['open_files_limit'] = open_files_limit
        result['Open_files'] = Open_files
        result['open_files_ratio'] = open_files_ratio

        if open_files_ratio >= 0.75:
            Issue = "open_files_limit参数设置需要优化"
            Reference = "https://dev.mysql.com/doc/refman/5.7/en/server-status-variables.html#open_files_limit"
            Description = "目前开启的文件数已经超过了最大文件数限制的75%。"
            Solution = "您需要调高open_files_limit参数值"
            return self.print_check(Issue=Issue, Category=Category, Description=Description, Reference=Reference,
                            Solution=Solution, result=result)
        else:
            Issue = "open_files_limit配置正常。"
            return self.print_check(Issue=Issue, Category=Category, result=result)


    def one(self,items):
        result = OrderedDict()
        items_h = getattr(self, items)
        result[items] = getattr(self, items)()
        return result

    def get_mysql_tuning(self,select='all'):
        self.get_mysql_variables()
        self.get_mysql_status()
        if select == 'all':
            result = OrderedDict()
            result['status_report'] = self.status_report()
            result['check_slowlog'] = self.check_slowlog()
            result['check_ratio_aborterd_connections'] = self.check_ratio_aborterd_connections()
            result['check_ratio_max_connections'] = self.check_ratio_max_connections()
            result['check_binlog'] = self.check_binlog()
            result['check_innodb'] = self.check_innodb()
            result['check_table_scans'] = self.check_table_scans()
            result['check_open_table'] = self.check_open_table()
            result['check_threads'] = self.check_threads()
            result['check_query_cache_type'] = self.check_query_cache_type()
            result['check_sort_buffer'] = self.check_sort_buffer()
            result['check_join_buffer_size'] = self.check_join_buffer_size()
            result['check_open_files_limit'] = self.check_open_files_limit()
            return result
        else:
            return self.one(select)


if __name__ == '__main__':
    get = Get_mysql_tuning()
    result = get.get_mysql_tuning()

    for k, v in result.iteritems():
        print '---' + k
        if 'report' in k:
            print v
        else:
            for a, b in v.iteritems():
                print a + ' : ' + str(b)
        print



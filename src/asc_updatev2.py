dir='/Users/One/Documents/Mario_Research/plate_routing/plates/'
files=['c66c45c83c10_Sum.asc','f2.1f2.2f2.3f6.1f6.2f8.1f8.2_Sum.asc',
        'f377f370f269_Sum.asc','f101f19f183f72_Sum.asc','f213f209f97f133_Sum.asc',
        'f166f151f300f103_Sum.asc']
files=['1_2_3_Sum.asc','n431n471n729n601n356_Sum.asc','A_B_Sum.asc',
        '419.1_353.1_419.2_353.2_Sum.asc','411.1_411.2_Sum.asc',
        '2155.1_2213.1_2155.2_2213.2_Sum.asc','1651.1_1846.1_1651.2_1846.2_Sum.asc',
        'n512n637n686n241n257n295_Sum.asc']
files=['1_2_3_Sum.asc','411.1_411.2_Sum.asc','419.1_353.1_419.2_353.2_Sum.asc','1651.1_1846.1_1651.2_1846.2_Sum.asc','2155.1_2213.1_2155.2_2213.2_Sum.asc','n431n471n729n601n356_Sum.asc','n512n637n686n241n257n295_Sum.asc','A_B_Sum.asc']

files=['A_B_test_Sum.asc']
import platefile
for f in files:
    x=platefile.ascfile(dir+f)
    x.writeWithChannels()	
